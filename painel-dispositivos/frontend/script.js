// ============================================================
// CONFIGURAÇÃO
// ============================================================

// Endereço onde a API (FastAPI) está rodando. Se você mudar a porta
// no back-end (ex: uvicorn main:app --port 8001), atualize aqui também.
const API_URL = "http://127.0.0.1:8000";

// ============================================================
// REFERÊNCIAS AOS ELEMENTOS DA TELA (HTML)
// Pegamos tudo uma vez só, no início, pra não ficar buscando
// o mesmo elemento toda hora dentro das funções.
// ============================================================
const form = document.getElementById("form-dispositivo");
const inputNome = document.getElementById("input-nome");
const inputLocal = document.getElementById("input-local");
const tabelaCorpo = document.getElementById("tabela-corpo");
const listaVazia = document.getElementById("lista-vazia");
const mensagemErro = document.getElementById("mensagem-erro");

// AC2: busca, filtros e cabeçalhos clicáveis (ordenação)
const inputBusca = document.getElementById("input-busca");
const filtroLocal = document.getElementById("filtro-local");
const filtroStatus = document.getElementById("filtro-status");
const cabecalhos = document.querySelectorAll("th[data-coluna]");

// AC2: estado da ordenação atual (coluna e direção).
// Começa em "id" (ordem de cadastro), igual ao comportamento da AC1.
let ordenarPor = "id";
let direcao = "asc";

// ============================================================
// TRATAMENTO DE ERRO
// ============================================================

/**
 * Mostra uma faixa de erro no topo da lista de dispositivos.
 * Chamada sempre que uma requisição para a API falha.
 */
function mostrarErro(texto) {
  mensagemErro.textContent = texto;
  mensagemErro.hidden = false;
}

/** Esconde a faixa de erro (usada quando uma chamada dá certo depois de ter falhado). */
function limparErro() {
  mensagemErro.hidden = true;
}

/**
 * Wrapper em volta do fetch nativo do navegador.
 *
 * Por que isso existe: sem esse cuidado, se a API estiver fora do ar
 * (ex: você esqueceu de rodar o uvicorn) ou o navegador bloquear a
 * requisição (CORS, ou o HTML aberto como arquivo local), o fetch()
 * lança uma exceção. Sem captura, o script para de executar
 * silenciosamente e a tela parece "travada", sem nenhum aviso.
 *
 * Essa função centraliza esse cuidado: toda chamada à API passa por
 * aqui, então só precisamos tratar o erro em um lugar.
 */
async function apiFetch(caminho, opcoes = {}) {
  let resposta;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, opcoes);
  } catch (erro) {
    // Esse "catch" pega falhas de rede/conexão (API fora do ar, CORS, etc.)
    mostrarErro(
      "Não foi possível conectar à API. Verifique se o back-end está rodando " +
        "(uvicorn main:app --reload) em " + API_URL + "."
    );
    throw erro; // repassa o erro pra quem chamou saber que falhou e não seguir o fluxo
  }

  if (!resposta.ok) {
    // A conexão funcionou, mas a API respondeu com erro (400, 404, 500...)
    let detalhe = "";
    try {
      const corpo = await resposta.json();
      detalhe = corpo.detail ? ` (${corpo.detail})` : "";
    } catch {
      // resposta sem corpo JSON, ignora
    }
    mostrarErro(`A API retornou um erro: ${resposta.status}${detalhe}`);
    throw new Error(`Erro HTTP ${resposta.status}`);
  }

  limparErro(); // deu tudo certo, garante que nenhum aviso antigo fique na tela
  return resposta;
}

// ============================================================
// CARREGAMENTO E RENDERIZAÇÃO DA LISTA DE DISPOSITIVOS
// ============================================================

/**
 * Busca os dispositivos na API e atualiza a tabela na tela.
 * É chamada sempre que algo muda: cadastro, remoção, filtro, busca ou ordenação.
 *
 * AC2: monta a URL com os filtros que estão preenchidos na tela.
 * Ex: /dispositivos?busca=totem&local=Loja+Centro&ordenar_por=nome&direcao=asc
 */
async function carregarDispositivos() {
  // URLSearchParams monta a parte "?chave=valor&..." já com os caracteres
  // especiais codificados (espaços, vírgulas, acentos).
  const params = new URLSearchParams();
  if (inputBusca.value.trim()) params.set("busca", inputBusca.value.trim());
  if (filtroLocal.value) params.set("local", filtroLocal.value);
  if (filtroStatus.value) params.set("status", filtroStatus.value);
  params.set("ordenar_por", ordenarPor);
  params.set("direcao", direcao);

  try {
    const resposta = await apiFetch(`/dispositivos?${params.toString()}`);
    const dispositivos = await resposta.json();
    renderizarTabela(dispositivos);
  } catch {
    // O erro já foi mostrado na tela pelo apiFetch — aqui só evitamos
    // que a exceção "suba" e quebre o restante da execução.
  }
}

/**
 * AC2: preenche o <select> de locais com os locais vindos da API (GET /locais).
 *
 * Usa uma rota própria (e não a lista de dispositivos já filtrada) porque,
 * depois de filtrar por um local, a lista só teria esse local — e o select
 * perderia todas as outras opções.
 */
async function carregarLocais() {
  try {
    const resposta = await apiFetch("/locais");
    const locais = await resposta.json();
    const selecionado = filtroLocal.value; // guarda a escolha atual antes de reconstruir

    filtroLocal.innerHTML = '<option value="">Todos os locais</option>';
    locais.forEach((local) => {
      const opcao = document.createElement("option");
      opcao.value = local;
      opcao.textContent = local;
      filtroLocal.appendChild(opcao);
    });

    // Se o local escolhido ainda existe, mantém selecionado; senão volta pra "Todos".
    filtroLocal.value = locais.includes(selecionado) ? selecionado : "";
  } catch {
    // Erro já exibido na tela pelo apiFetch.
  }
}

/** Recria as linhas da tabela a partir da lista de dispositivos vinda da API. */
function renderizarTabela(dispositivos) {
  tabelaCorpo.innerHTML = "";
  listaVazia.hidden = dispositivos.length > 0;

  dispositivos.forEach((d) => {
    const linha = document.createElement("tr");
    const dataFormatada = new Date(d.ultima_sincronizacao).toLocaleString("pt-BR");

    linha.innerHTML = `
      <td>${d.nome}</td>
      <td>${d.local}</td>
      <td><span class="status-pill ${d.status}">${d.status}</span></td>
      <td>${dataFormatada}</td>
      <td class="acoes">
        <button class="perigo" data-id="${d.id}">Remover</button>
      </td>
    `;
    tabelaCorpo.appendChild(linha);
  });
}

// ============================================================
// AÇÕES DO USUÁRIO (eventos)
// ============================================================

// Envio do formulário de cadastro
form.addEventListener("submit", async (evento) => {
  evento.preventDefault(); // impede o navegador de recarregar a página (comportamento padrão de <form>)

  try {
    await apiFetch("/dispositivos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: inputNome.value, local: inputLocal.value }),
    });
    // Só limpa o formulário e recarrega a lista se o cadastro deu certo.
    inputNome.value = "";
    inputLocal.value = "";
    await carregarLocais(); // AC2: o local cadastrado pode ser novo no filtro
    await carregarDispositivos();
  } catch {
    // Erro já exibido na tela pelo apiFetch; não faz nada além disso.
  }
});

// Clique no botão "Remover" de cada linha da tabela.
// Usamos delegação de evento (um listener só na tabela, não um por botão)
// porque as linhas são recriadas toda vez que a lista atualiza.
tabelaCorpo.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("button");
  if (!botao) return; // clique fora de um botão (ex: numa célula vazia), ignora

  try {
    await apiFetch(`/dispositivos/${botao.dataset.id}`, { method: "DELETE" });
    await carregarLocais(); // AC2: o local removido pode não existir mais
    await carregarDispositivos();
  } catch {
    // Erro já exibido na tela pelo apiFetch.
  }
});

// ============================================================
// AC2: BUSCA, FILTROS E ORDENAÇÃO
// ============================================================

// Trocar o local ou o status recarrega a lista já filtrada.
filtroLocal.addEventListener("change", carregarDispositivos);
filtroStatus.addEventListener("change", carregarDispositivos);

// Busca por nome enquanto digita. O setTimeout espera 300 ms sem digitação
// antes de consultar a API — assim não fazemos uma requisição por letra.
let temporizadorBusca;
inputBusca.addEventListener("input", () => {
  clearTimeout(temporizadorBusca);
  temporizadorBusca = setTimeout(carregarDispositivos, 300);
});

// Clique no cabeçalho da tabela: ordena pela coluna clicada.
// Clicar de novo na mesma coluna inverte a direção (crescente <-> decrescente).
cabecalhos.forEach((th) => {
  th.addEventListener("click", () => {
    const coluna = th.dataset.coluna;
    direcao = coluna === ordenarPor && direcao === "asc" ? "desc" : "asc";
    ordenarPor = coluna;
    atualizarSetas();
    carregarDispositivos();
  });
});

/** Mostra ▲ ou ▼ só no cabeçalho da coluna usada na ordenação atual. */
function atualizarSetas() {
  cabecalhos.forEach((th) => {
    const ativa = th.dataset.coluna === ordenarPor;
    th.classList.toggle("ativa", ativa);
    th.querySelector(".seta").textContent = ativa ? (direcao === "asc" ? "▲" : "▼") : "";
  });
}

// ============================================================
// INICIALIZAÇÃO
// Carrega os locais do filtro e a lista assim que a página abre,
// sem precisar de nenhuma ação do usuário.
// ============================================================
carregarLocais();
carregarDispositivos();
