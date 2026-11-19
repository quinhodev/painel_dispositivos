// ============================================================
// CONFIGURAÇÃO
// ============================================================

// Endereço onde a API (FastAPI) está rodando. Se você mudar a porta
// no back-end (ex: uvicorn main:app --port 8001), atualize aqui também.
const API_URL = "http://127.0.0.1:8000";

// AC3: de quanto em quanto tempo (em milissegundos) a lista é buscada de novo
// na API sozinha, para o status e o "há quanto tempo" acompanharem o que
// está acontecendo sem precisar recarregar a página.
const INTERVALO_ATUALIZACAO_MS = 10000;

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

// FINAL: login, dashboard no topo e exportação
const CHAVE_TOKEN = "painel_token"; // nome com que o token fica guardado no navegador
const telaLogin = document.getElementById("tela-login");
const conteudoPrincipal = document.getElementById("conteudo-principal");
const topbarAcoes = document.getElementById("topbar-acoes");
const formLogin = document.getElementById("form-login");
const inputUsuario = document.getElementById("input-usuario");
const inputSenha = document.getElementById("input-senha");
const loginErro = document.getElementById("login-erro");
const botaoSair = document.getElementById("botao-sair");
const botaoExportar = document.getElementById("botao-exportar");
const resumoTotal = document.getElementById("resumo-total");
const resumoOnline = document.getElementById("resumo-online");
const resumoOffline = document.getElementById("resumo-offline");
const resumoPercentual = document.getElementById("resumo-percentual");

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
  // FINAL: toda chamada leva o token do login no cabeçalho Authorization.
  const token = obterToken();
  const headers = { ...(opcoes.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resposta;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, { ...opcoes, headers });
  } catch (erro) {
    // Esse "catch" pega falhas de rede/conexão (API fora do ar, CORS, etc.)
    mostrarErro(
      "Não foi possível conectar à API. Verifique se o back-end está rodando " +
        "(uvicorn main:app --reload) em " + API_URL + "."
    );
    throw erro; // repassa o erro pra quem chamou saber que falhou e não seguir o fluxo
  }

  if (!resposta.ok) {
    // FINAL: 401 = não está logado ou a sessão expirou -> volta para a tela de login.
    if (resposta.status === 401) {
      encerrarSessao("Sua sessão expirou. Entre novamente.");
      throw new Error("Não autenticado");
    }

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
 * FINAL: monta os parâmetros de URL a partir dos filtros e da ordenação
 * que estão na tela. Usada tanto pela lista quanto pela exportação CSV,
 * para o relatório sair exatamente como o usuário está vendo.
 */
function montarParametros() {
  // URLSearchParams monta a parte "?chave=valor&..." já com os caracteres
  // especiais codificados (espaços, vírgulas, acentos).
  const params = new URLSearchParams();
  if (inputBusca.value.trim()) params.set("busca", inputBusca.value.trim());
  if (filtroLocal.value) params.set("local", filtroLocal.value);
  if (filtroStatus.value) params.set("status", filtroStatus.value);
  params.set("ordenar_por", ordenarPor);
  params.set("direcao", direcao);
  return params;
}

/**
 * Busca os dispositivos na API e atualiza a tabela na tela.
 * É chamada sempre que algo muda: cadastro, remoção, filtro, busca ou ordenação.
 *
 * AC2: monta a URL com os filtros que estão preenchidos na tela.
 * Ex: /dispositivos?busca=totem&local=Loja+Centro&ordenar_por=nome&direcao=asc
 */
async function carregarDispositivos() {
  const params = montarParametros();

  try {
    const resposta = await apiFetch(`/dispositivos?${params.toString()}`);
    const dispositivos = await resposta.json();
    renderizarTabela(dispositivos);
    carregarResumo(); // FINAL: mantém o dashboard do topo em dia com a lista
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

/**
 * AC3: converte a data vinda da API em um objeto Date.
 *
 * O back-end guarda a data em UTC, mas o JSON chega sem fuso (sem o "Z"
 * no final). Sem o "Z", o navegador entende como horário local e a conta
 * de "há quanto tempo" sai errada (a diferença seria de algumas horas).
 */
function paraDataUTC(texto) {
  const temFuso = /Z|[+-]\d\d:\d\d$/.test(texto);
  return new Date(temFuso ? texto : texto + "Z");
}

/** AC3: transforma segundos em um texto curto ("há 30 s", "há 2 min", "há 3 h"...). */
function formatarTempo(segundos) {
  if (segundos < 5) return "agora";
  if (segundos < 60) return `há ${segundos} s`;
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `há ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `há ${horas} h`;
  return `há ${Math.floor(horas / 24)} d`;
}

/** AC3: escolhe a cor do indicador conforme o tempo (verde, âmbar ou vermelho). */
function classeTempo(segundos) {
  if (segundos < 60) return "tempo-recente";
  if (segundos < 300) return "tempo-medio";
  return "tempo-antigo";
}

/**
 * FINAL: troca caracteres especiais de HTML por versões seguras.
 * Sem isso, um nome como "<b>x</b>" (ou pior, um <script>) digitado no
 * cadastro seria interpretado como HTML ao montar a tabela com innerHTML.
 */
function escaparHtml(texto) {
  return String(texto)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Recria as linhas da tabela a partir da lista de dispositivos vinda da API. */
function renderizarTabela(dispositivos) {
  tabelaCorpo.innerHTML = "";
  listaVazia.hidden = dispositivos.length > 0;

  dispositivos.forEach((d) => {
    const linha = document.createElement("tr");
    const dataSincronizacao = paraDataUTC(d.ultima_sincronizacao);
    const dataFormatada = dataSincronizacao.toLocaleString("pt-BR");

    // AC3: guardamos o instante da sincronização no próprio elemento (data-instante)
    // para o relógio da tela (atualizarTempos) recalcular o "há quanto tempo"
    // a cada segundo, sem precisar chamar a API.
    linha.innerHTML = `
      <td>${escaparHtml(d.nome)}</td>
      <td>${escaparHtml(d.local)}</td>
      <td><span class="status-pill ${escaparHtml(d.status)}">${escaparHtml(d.status)}</span></td>
      <td>${dataFormatada}</td>
      <td class="tempo" data-instante="${dataSincronizacao.getTime()}"></td>
      <td class="acoes">
        <button class="secundario" data-acao="heartbeat" data-id="${d.id}">Heartbeat</button>
        <button class="perigo" data-acao="remover" data-id="${d.id}">Remover</button>
      </td>
    `;
    tabelaCorpo.appendChild(linha);
  });

  atualizarTempos(); // já preenche o "há quanto tempo" sem esperar o próximo segundo
}

/**
 * AC3: recalcula o "há quanto tempo" de todas as linhas da tabela.
 * Roda uma vez por segundo (ver INICIALIZAÇÃO) e só mexe na tela.
 */
function atualizarTempos() {
  document.querySelectorAll("td.tempo").forEach((celula) => {
    const instante = Number(celula.dataset.instante);
    const segundos = Math.max(0, Math.floor((Date.now() - instante) / 1000));
    celula.textContent = formatarTempo(segundos);
    celula.className = `tempo ${classeTempo(segundos)}`;
  });
}

// ============================================================
// FINAL: LOGIN E SESSÃO
// ============================================================

/** Devolve o token guardado no navegador (ou null se não estiver logado). */
function obterToken() {
  return sessionStorage.getItem(CHAVE_TOKEN);
}

/** Mostra só a tela de login (e opcionalmente uma mensagem, como "sessão expirada"). */
function mostrarTelaLogin(mensagem = "") {
  conteudoPrincipal.hidden = true;
  topbarAcoes.hidden = true;
  telaLogin.hidden = false;
  loginErro.textContent = mensagem;
  loginErro.hidden = !mensagem;
  inputUsuario.focus();
}

/** Mostra o painel e carrega os dados (chamada depois de um login válido). */
function mostrarApp() {
  telaLogin.hidden = true;
  conteudoPrincipal.hidden = false;
  topbarAcoes.hidden = false;
  carregarLocais();
  carregarDispositivos();
}

/** Esquece o token e volta para o login. */
function encerrarSessao(mensagem = "") {
  sessionStorage.removeItem(CHAVE_TOKEN);
  mostrarTelaLogin(mensagem);
}

// Envio do formulário de login.
// Aqui usamos fetch direto (e não o apiFetch) porque um 401 neste caso
// significa "senha errada", e não "sessão expirada".
formLogin.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  try {
    const resposta = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario: inputUsuario.value, senha: inputSenha.value }),
    });

    if (!resposta.ok) {
      loginErro.textContent =
        resposta.status === 401 ? "Usuário ou senha inválidos." : `Erro ao entrar (${resposta.status}).`;
      loginErro.hidden = false;
      return;
    }

    const dados = await resposta.json();
    sessionStorage.setItem(CHAVE_TOKEN, dados.token);
    inputSenha.value = "";
    loginErro.hidden = true;
    mostrarApp();
  } catch {
    loginErro.textContent = "Não foi possível conectar à API. Verifique se o back-end está rodando.";
    loginErro.hidden = false;
  }
});

// Botão "Sair": avisa o servidor (para invalidar o token) e volta para o login.
botaoSair.addEventListener("click", async () => {
  try {
    await apiFetch("/logout", { method: "POST" });
  } catch {
    // Mesmo que o servidor não responda, a sessão é encerrada aqui.
  }
  encerrarSessao();
});

// ============================================================
// FINAL: DASHBOARD E EXPORTAÇÃO CSV
// ============================================================

/** Busca as métricas gerais (GET /dashboard/resumo) e preenche o topo da tela. */
async function carregarResumo() {
  try {
    const resposta = await apiFetch("/dashboard/resumo");
    const resumo = await resposta.json();
    resumoTotal.textContent = resumo.total;
    resumoOnline.textContent = resumo.online;
    resumoOffline.textContent = resumo.offline;
    resumoPercentual.textContent =
      resumo.percentual_online.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
  } catch {
    // Erro já exibido na tela pelo apiFetch.
  }
}

/**
 * Baixa o relatório CSV com os mesmos filtros e ordenação da tela.
 *
 * Não dá para usar um link comum (<a href>) porque a rota exige o token no
 * cabeçalho. Por isso buscamos o arquivo com fetch, transformamos em um
 * "blob" e disparamos o download por um link temporário.
 */
async function exportarCSV() {
  try {
    const resposta = await apiFetch(`/relatorio/csv?${montarParametros().toString()}`);
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "dispositivos.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch {
    // Erro já exibido na tela pelo apiFetch.
  }
}

botaoExportar.addEventListener("click", exportarCSV);

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

// Clique nos botões de cada linha da tabela ("Heartbeat" e "Remover").
// Usamos delegação de evento (um listener só na tabela, não um por botão)
// porque as linhas são recriadas toda vez que a lista atualiza.
tabelaCorpo.addEventListener("click", async (evento) => {
  const botao = evento.target.closest("button");
  if (!botao) return; // clique fora de um botão (ex: numa célula vazia), ignora

  const id = botao.dataset.id;

  try {
    if (botao.dataset.acao === "heartbeat") {
      // AC3: simula o dispositivo avisando que está ativo (vira "online").
      await apiFetch(`/dispositivos/${id}/heartbeat`, { method: "POST" });
    } else {
      await apiFetch(`/dispositivos/${id}`, { method: "DELETE" });
      await carregarLocais(); // AC2: o local removido pode não existir mais
    }
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
// FINAL: se já existe um login guardado, entra direto no painel e carrega
// os dados; senão, mostra a tela de login.
// ============================================================
if (obterToken()) {
  mostrarApp();
} else {
  mostrarTelaLogin();
}

// AC3: monitoramento em tempo (quase) real.
// - a cada INTERVALO_ATUALIZACAO_MS busca a lista de novo (pega mudanças de status);
//   (FINAL: só enquanto estiver logado)
// - a cada 1 segundo só recalcula o "há quanto tempo" na tela.
setInterval(() => {
  if (obterToken()) carregarDispositivos();
}, INTERVALO_ATUALIZACAO_MS);
setInterval(atualizarTempos, 1000);
