/* =============================================
   MENU MOBILE
   ============================================= */
(function () {
  var toggler = document.querySelector('.navbar-toggler');
  var collapse = document.querySelector('.navbar-collapse');
  if (!toggler || !collapse) return;

  toggler.addEventListener('click', function () {
    var aberto = collapse.classList.toggle('open');
    toggler.setAttribute('aria-expanded', aberto);
  });
})();

/* =============================================
   STICKY HEADER
   ============================================= */
(function () {
  var header = document.getElementById('header-fix');
  if (!header) return;

  var headerHeight = header.offsetHeight;
  var tick = false;

  window.addEventListener('scroll', function () {
    if (tick) return;
    tick = true;
    requestAnimationFrame(function () {
      if (window.scrollY > headerHeight) {
        header.classList.add('active');
        document.body.style.paddingTop = headerHeight + 'px';
      } else {
        header.classList.remove('active');
        document.body.style.paddingTop = '';
      }
      tick = false;
    });
  }, { passive: true });
})();

/* =============================================
   BANNER SLIDER
   ============================================= */
(function () {
  var items = document.querySelectorAll('.banner-item');
  if (items.length <= 1) return;

  var atual = 0;
  var intervalo;

  function ir(idx) {
    items[atual].classList.remove('active');
    atual = (idx + items.length) % items.length;
    items[atual].classList.add('active');
  }

  function iniciar() {
    intervalo = setInterval(function () { ir(atual + 1); }, 5000);
  }

  function reiniciar() {
    clearInterval(intervalo);
    iniciar();
  }

  var prev = document.querySelector('.banner-prev');
  var next = document.querySelector('.banner-next');

  if (prev) prev.addEventListener('click', function () { ir(atual - 1); reiniciar(); });
  if (next) next.addEventListener('click', function () { ir(atual + 1); reiniciar(); });

  iniciar();
})();

/* =============================================
   GALERIA — TROCA DE IMAGEM PRINCIPAL
   ============================================= */
function trocarImagem(thumb) {
  var principal = document.getElementById('img-principal');
  if (!principal) return;
  principal.src = thumb.src;
  document.querySelectorAll('.galeria-thumbs__item').forEach(function (t) {
    t.classList.remove('ativo');
  });
  thumb.classList.add('ativo');
}

/* =============================================
   TABS (car detail page)
   ============================================= */
(function () {
  var links = document.querySelectorAll('.nav-tab-link');
  if (!links.length) return;

  links.forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      var target = this.getAttribute('data-tab');

      // Update nav links
      links.forEach(function (l) { l.classList.remove('active'); });
      this.classList.add('active');

      // Update panes
      document.querySelectorAll('.tab-pane').forEach(function (pane) {
        pane.classList.remove('active');
      });
      var pane = document.getElementById('tab-' + target);
      if (pane) pane.classList.add('active');
    });
  });
})();

/* =============================================
   FILTROS DE CARROS
   ============================================= */
(function () {
  var filtroMarca = document.getElementById('filtro-marca');
  var filtroCombustivel = document.getElementById('filtro-combustivel');
  var filtroCambio = document.getElementById('filtro-cambio');
  var limpar = document.getElementById('limpar-filtros');
  var itens = document.querySelectorAll('.carro-grid-item');
  var aviso = document.getElementById('carros-vazio');

  if (!filtroMarca) return;

  function filtrar() {
    var marca = filtroMarca.value.toLowerCase();
    var comb = filtroCombustivel.value.toLowerCase();
    var cambio = filtroCambio.value.toLowerCase();
    var visiveis = 0;

    itens.forEach(function (item) {
      var ok =
        (!marca || item.dataset.marca === marca) &&
        (!comb || item.dataset.combustivel === comb) &&
        (!cambio || item.dataset.cambio === cambio);

      item.style.display = ok ? '' : 'none';
      if (ok) visiveis++;
    });

    if (aviso) aviso.style.display = visiveis === 0 ? '' : 'none';
  }

  filtroMarca.addEventListener('change', filtrar);
  filtroCombustivel.addEventListener('change', filtrar);
  filtroCambio.addEventListener('change', filtrar);

  if (limpar) {
    limpar.addEventListener('click', function () {
      filtroMarca.value = '';
      filtroCombustivel.value = '';
      filtroCambio.value = '';
      filtrar();
    });
  }
})();

/* =============================================
   SCROLL TO TOP
   ============================================= */
(function () {
  var btn = document.getElementById('scrollup');
  if (!btn) return;

  var stTick = false;
  window.addEventListener('scroll', function () {
    if (stTick) return;
    stTick = true;
    requestAnimationFrame(function () {
      btn.style.display = window.scrollY > 400 ? 'block' : 'none';
      stTick = false;
    });
  }, { passive: true });

  btn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();
