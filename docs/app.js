"use strict";

const statusEl = document.getElementById("status");
const lookupForm = document.getElementById("lookup-form");
const batchForm = document.getElementById("batch-form");
const resultsEl = document.getElementById("results");
const lookupButton = document.getElementById("lookup-button");
const batchButton = document.getElementById("batch-button");
let runtimePromise;

function setStatus(message) {
  statusEl.textContent = message;
}

function runtime() {
  if (!runtimePromise) {
    runtimePromise = (async () => {
      setStatus("Loading Python runtime (first use requires internet)...");
      const pyodide = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/"
      });
      const response = await fetch("./loinc_mapper.py");
      if (!response.ok) throw new Error("Cannot load the mapper source.");
      pyodide.FS.writeFile("/tmp/loinc_mapper.py", await response.text());
      await pyodide.runPythonAsync("import sys\nsys.path.insert(0, '/tmp')\nimport loinc_mapper, json");
      setStatus("Python ready · mapping performed locally in this browser");
      return pyodide;
    })().catch((err) => {
      runtimePromise = null;
      throw err;
    });
  }
  return runtimePromise;
}

function setBusy(busy) {
  lookupButton.disabled = busy;
  batchButton.disabled = busy;
}

function renderResults(data) {
  resultsEl.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = data.top_hit === "no match" ? "No candidate matches" : "Candidate matches";
  resultsEl.append(heading);

  const note = document.createElement("p");
  note.className = "muted";
  note.textContent = "Scores are heuristic ranking values, not calibrated probabilities.";
  resultsEl.append(note);

  if (!data.all.length) return;
  const table = document.createElement("table");
  const header = document.createElement("thead");
  const row = document.createElement("tr");
  for (const title of ["LOINC code and label", "Score"]) {
    const th = document.createElement("th");
    th.textContent = title;
    row.append(th);
  }
  header.append(row);
  table.append(header);
  const body = document.createElement("tbody");
  for (const match of data.all) {
    const tr = document.createElement("tr");
    const cell1 = document.createElement("td");
    const cell2 = document.createElement("td");
    cell1.textContent = match[1];
    cell2.textContent = String(match[0]);
    tr.append(cell1, cell2);
    body.append(tr);
  }
  table.append(body);
  resultsEl.append(table);
}

lookupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  try {
    const query = document.getElementById("query").value.trim();
    const count = Number(document.getElementById("max-results").value);
    if (!query) throw new Error("Enter a laboratory test name or LOINC code.");
    if (!Number.isInteger(count) || count < 1 || count > 20) {
      throw new Error("Results must be between 1 and 20.");
    }
    const pyodide = await runtime();
    pyodide.globals.set("user_query", query);
    pyodide.globals.set("result_limit", count);
    const output = await pyodide.runPythonAsync(
      "json.dumps(loinc_mapper.lookup(user_query, max_results=result_limit))"
    );
    renderResults(JSON.parse(output));
    setStatus("Lookup complete · check candidate code and specimen details before use");
  } catch (error) {
    setStatus("Lookup error: " + error.message);
  } finally {
    setBusy(false);
  }
});

batchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  try {
    const input = document.getElementById("csv-file").files[0];
    if (!input) throw new Error("Select a CSV file.");
    if (input.size > 1024 * 1024) throw new Error("CSV file must be at most 1 MiB.");
    const pyodide = await runtime();
    pyodide.FS.writeFile("/tmp/loinc_input.csv", new Uint8Array(await input.arrayBuffer()));
    const count = await pyodide.runPythonAsync(
      "len(loinc_mapper.process_csv('/tmp/loinc_input.csv', '/tmp/loinc_output.csv'))"
    );
    const bytes = pyodide.FS.readFile("/tmp/loinc_output.csv");
    const url = URL.createObjectURL(new Blob([bytes], {type: "text/csv;charset=utf-8"}));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "loinc_mapping_results.csv";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    setStatus("Mapped " + count + " rows · downloaded results CSV");
  } catch (error) {
    setStatus("CSV error: " + error.message);
  } finally {
    setBusy(false);
  }
});
