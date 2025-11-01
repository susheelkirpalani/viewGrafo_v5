// static/main.js
// Lógica frontend para interactuar con server.py (versión final)
// Cambios aplicados:
// - Se eliminó la lógica del subtítulo
// - Placeholders de subpreguntas --> "Ingresa una respuesta o pregunta"
// - Botones: btnExportar (window.location.href = "/export_json"), btnBorrar (confirm + POST /reset + recarga UI)
// - Se protege la lectura de elementos inexistentes para evitar errores en consola

async function iniciar() {
  await fetch("/iniciar"); // reinicia (si se desea)
  cargarPreguntaActual();
}

async function cargarPreguntaActual() {
  const res = await fetch("/obtener_pregunta_actual");
  const data = await res.json();
  const cont = document.getElementById("app-content");
  const pb = document.getElementById("progress-bar");
  const pathInfo = document.getElementById("path-info");

  if (!data.existe) {
    cont.innerHTML = `
      <div>
        <p class="font-semibold mb-3">🔹 Escribe la pregunta raíz (editable):</p>
        <div class="flex gap-2 items-center">
          <input id="raiz-texto" class="border rounded p-2 flex-1" placeholder="Ej. ¿Qué comida salvadoreña deseas?" />
          <button onclick="crearRaiz()" class="px-3 py-2 rounded bg-primary text-white">Crear raíz</button>
        </div>
      </div>
    `;
    if (pb) pb.style.width = "0%";
    if (pathInfo) pathInfo.textContent = "";
    return;
  }

  // mostrar nodo actual y sus opciones
  let html = `<div class="mb-4"><p class="font-bold text-lg">${data.texto}</p></div>`;

  // mostrar opciones disponibles como botones
  if (data.opciones && data.opciones.length > 0) {
    html += `<div class="mb-3 space-y-2">`;
    data.opciones.forEach((o) => {
      // si la opcion es final y ya tiene respuesta, mostrar badge
      let badge = o.tiene_respuesta ? ' <span class="text-sm ml-2 text-green-700"> (respondida)</span>' : '';
      html += `<div class="flex items-center justify-between gap-2">
        <button class="flex-1 text-left border rounded px-3 py-2 hover:bg-gray-50" onclick="avanzar('${o.id}', ${o.es_final})">${o.texto}${badge}</button>
        ${o.es_final ? '<span class="text-sm px-2 py-1 rounded bg-yellow-100 text-yellow-800">Última</span>' : ''}
      </div>`;
    });
    html += `</div>`;
  }

  // form para agregar subpreguntas (cajas) con toggle "última pregunta"
  html += `
    <div class="mt-4 border p-4 rounded">
      <p class="font-medium mb-2">Agregar hasta 3 subpreguntas (cada una puede marcarse como "última")</p>
      <div class="space-y-2">
        <div class="flex gap-2 items-center">
          <input id="sub1" class="border rounded p-2 flex-1" placeholder="Ingresa una respuesta o pregunta" />
          <label class="flex items-center gap-1"><input type="checkbox" id="ulti1"/> Última</label>
        </div>
        <div class="flex gap-2 items-center">
          <input id="sub2" class="border rounded p-2 flex-1" placeholder="Ingresa una respuesta o pregunta" />
          <label class="flex items-center gap-1"><input type="checkbox" id="ulti2"/> Última</label>
        </div>
        <div class="flex gap-2 items-center">
          <input id="sub3" class="border rounded p-2 flex-1" placeholder="Ingresa una respuesta o pregunta" />
          <label class="flex items-center gap-1"><input type="checkbox" id="ulti3"/> Última</label>
        </div>
        <div class="mt-2">
          <button onclick="agregarSubpreguntas()" class="px-3 py-2 rounded bg-primary text-white">Guardar subpreguntas</button>
          ${data.tienePadre ? `<button onclick="retroceder()" class="ml-2 px-3 py-2 rounded bg-red-500 text-white">⬅️ Retroceder</button>` : ''}
        </div>
      </div>
    </div>
  `;

  cont.innerHTML = html;

  if (pb) pb.style.width = data.progressPercent + "%";
  if (pathInfo) pathInfo.textContent = "Ruta: " + (data.pathLabels ? data.pathLabels.join(" → ") : "");

  // forzar recarga del grafo
  const grafoFrame = document.getElementById("grafo-frame");
  if (grafoFrame) grafoFrame.src = "/ver_grafo?" + new Date().getTime();
}

async function crearRaiz() {
  const textoEl = document.getElementById("raiz-texto");
  const texto = textoEl ? textoEl.value.trim() : "";
  if (!texto) return alert("Ingresa un texto para la raíz.");
  await fetch("/nueva_pregunta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto }),
  });
  cargarPreguntaActual();
}

async function agregarSubpreguntas() {
  const sub1El = document.getElementById("sub1");
  const sub2El = document.getElementById("sub2");
  const sub3El = document.getElementById("sub3");

  const sub1 = sub1El ? sub1El.value.trim() : "";
  const sub2 = sub2El ? sub2El.value.trim() : "";
  const sub3 = sub3El ? sub3El.value.trim() : "";

  const lista = [sub1, sub2, sub3].filter(s => s.length > 0);
  if (lista.length === 0) return alert("Agrega al menos una subpregunta.");
  // paralelamente tomar si son ultimas
  const ult1 = !!(document.getElementById("ulti1") && document.getElementById("ulti1").checked);
  const ult2 = !!(document.getElementById("ulti2") && document.getElementById("ulti2").checked);
  const ult3 = !!(document.getElementById("ulti3") && document.getElementById("ulti3").checked);
  const ultimas = [ult1, ult2, ult3].slice(0, lista.length);
  await fetch("/nueva_pregunta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subpreguntas: lista, ultimas }),
  });
  cargarPreguntaActual();
}

async function avanzar(id, es_final) {
  // Si es final: mostrar prompt para responder (UI)
  if (es_final) {
    // mostrar modal simple con prompt
    const respuesta = prompt("Esta opción está marcada como ÚLTIMA. Escribe la respuesta final:");
    if (respuesta === null) return; // cancel
    const body = { id, respuesta, finalizar: true };
    const res = await fetch("/nueva_pregunta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.ok) {
      alert("Respuesta guardada y finalizada.");
      cargarPreguntaActual();
      return;
    } else {
      alert("Error: " + (data.error || "no se pudo finalizar"));
      return;
    }
  }

  // Si no es final, navegar hacia ese nodo
  await fetch("/nueva_pregunta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, avanzar: true }),
  });
  cargarPreguntaActual();
}

async function retroceder() {
  await fetch("/retroceder");
  cargarPreguntaActual();
}

// Edición de título (UI local)
// Nota: la lógica del subtítulo fue eliminada (no existe subtítulo en el index final)
document.addEventListener("DOMContentLoaded", () => {
  // iniciar carga
  cargarPreguntaActual();

  const editarTituloBtn = document.getElementById("editar-titulo");
  if (editarTituloBtn) {
    editarTituloBtn.addEventListener("click", () => {
      const tituloText = document.getElementById("titulo-text");
      const nuevo = prompt("Editar título principal:", tituloText ? tituloText.textContent : "");
      if (nuevo !== null && nuevo.trim() !== "") {
        if (tituloText) tituloText.textContent = nuevo.trim();
      }
    });
  }

  // Botón Exportar JSON (descarga directa)
  const btnExportar = document.getElementById("btnExportar");
  if (btnExportar) {
    btnExportar.addEventListener("click", (e) => {
      // iniciamos la descarga directa
      // esto hará que el navegador inicie el FileResponse desde /export_json
      window.location.href = "/export_json";
    });
  }

  // Botón Borrar Todo (confirm + reset)
  const btnBorrar = document.getElementById("btnBorrar");
  if (btnBorrar) {
    btnBorrar.addEventListener("click", async () => {
      const ok = confirm("¿Seguro que quieres borrar todo el árbol? Esta acción no se puede deshacer.");
      if (!ok) return;
      try {
        await fetch("/reset", { method: "POST" });
      } catch (err) {
        console.error("Error al resetear:", err);
      }
      // recargar estado inicial sin raíz
      cargarPreguntaActual();
      // también forzar recarga del iframe del grafo
      const grafoFrame = document.getElementById("grafo-frame");
      if (grafoFrame) grafoFrame.src = "/ver_grafo?" + new Date().getTime();
    });
  }
});
