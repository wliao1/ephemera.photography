// Gallery pages, like the original Squarespace site:
// - photos flow into up to 3 columns, each photo going to the shortest column (masonry);
// - clicking a photo shows it alone with PREV / NEXT and SHOW THUMBNAILS (arrow keys and swipe
//   work too). The open photo is in the address as #N, so it can be shared and Back returns.
(function () {
  var gallery = document.querySelector('.gallery');
  if (!gallery) return;
  var items = Array.prototype.slice.call(gallery.querySelectorAll('.ph'));
  var total = items.length;
  var GAP = 10, MIN_COLUMN = 300, MAX_COLUMNS = 3;
  var columnCount = 0;

  function arrange() {
    var width = gallery.clientWidth;
    var n = Math.max(1, Math.min(MAX_COLUMNS, Math.floor((width + GAP) / (MIN_COLUMN + GAP))));
    if (n === columnCount || !width) return;
    columnCount = n;
    var columnWidth = (width - GAP * (n - 1)) / n;
    var columns = [], heights = [];
    for (var c = 0; c < n; c++) {
      var col = document.createElement('div');
      col.className = 'col';
      columns.push(col);
      heights.push(0);
    }
    items.forEach(function (a) {
      var img = a.querySelector('img');
      var shortest = heights.indexOf(Math.min.apply(null, heights));
      columns[shortest].appendChild(a); // moves the photo out of its old column
      heights[shortest] += columnWidth * img.getAttribute('height') / img.getAttribute('width') + GAP;
    });
    while (gallery.firstChild) gallery.removeChild(gallery.firstChild); // old, now-empty columns
    columns.forEach(function (col) { gallery.appendChild(col); });
    gallery.classList.add('ready');
  }

  var pending = false;
  window.addEventListener('resize', function () {
    if (pending) return;
    pending = true;
    requestAnimationFrame(function () { pending = false; arrange(); });
  });
  arrange();

  // One photo at a time
  var slide = document.createElement('div');
  slide.className = 'slide';
  slide.innerHTML = '<img alt="">' +
    '<div class="controls"><div class="row"><button type="button" class="prev">Prev</button>' +
    '<span class="sep">/</span><button type="button" class="next">Next</button></div>' +
    '<div class="row"><button type="button" class="thumbs">Show thumbnails</button></div></div>';
  gallery.parentNode.insertBefore(slide, gallery.nextSibling);
  var img = slide.querySelector('img');
  var index = -1;
  var pushed = false;   // true when opening a photo added a history entry
  var savedScroll = 0;
  var startX = null;

  function show(i) {
    if (index === -1) savedScroll = window.pageYOffset;
    index = (i + total) % total;
    var a = items[index];
    img.src = a.getAttribute('data-full');
    img.alt = a.querySelector('img').alt;
    document.body.classList.add('single');
    window.scrollTo(0, 0);
    new Image().src = items[(index + 1) % total].getAttribute('data-full');
  }

  function hide() {
    if (index === -1) return;
    document.body.classList.remove('single');
    index = -1;
    arrange();
    window.scrollTo(0, savedScroll);
  }

  function open(i) {
    show(i);
    history.pushState({ photo: true }, '', '#' + (index + 1));
    pushed = true;
  }

  function go(step) {
    show(index + step);
    history.replaceState({ photo: true }, '', '#' + (index + 1));
  }

  function close() {
    if (pushed) {
      pushed = false;
      history.back(); // the popstate handler returns to the grid
    } else {
      hide();
      history.replaceState(null, '', location.pathname + location.search);
    }
  }

  function fromHash() {
    var n = parseInt(location.hash.slice(1), 10);
    if (n >= 1 && n <= total) show(n - 1); else hide();
  }

  items.forEach(function (a, i) {
    a.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // keep open-in-new-tab
      e.preventDefault();
      open(i);
    });
  });
  img.addEventListener('click', function () { go(1); });
  slide.querySelector('.prev').addEventListener('click', function () { go(-1); });
  slide.querySelector('.next').addEventListener('click', function () { go(1); });
  slide.querySelector('.thumbs').addEventListener('click', close);
  document.addEventListener('keydown', function (e) {
    if (index === -1) return;
    if (e.key === 'ArrowRight') go(1);
    else if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'Escape') close();
  });
  slide.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
  slide.addEventListener('touchend', function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    startX = null;
    if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
  });
  window.addEventListener('popstate', function () { pushed = false; fromHash(); });
  fromHash();
})();
