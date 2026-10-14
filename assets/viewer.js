// Full-screen photo viewer for series pages: click a photo; arrows/swipe to move; Esc or × to close.
// Each open photo gets an address like #12, so it can be shared and the back button closes it.
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.grid .ph'));
  if (!links.length) return;
  var total = links.length;
  var index = -1;
  var pushed = false; // true when we added a history entry by opening a photo
  var startX = null;

  var box = document.createElement('div');
  box.className = 'viewer';
  box.hidden = true;
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Photo viewer');
  box.innerHTML = '<img alt="">' +
    '<button class="prev" type="button" aria-label="Previous photo">&#8249;</button>' +
    '<button class="next" type="button" aria-label="Next photo">&#8250;</button>' +
    '<button class="close" type="button" aria-label="Close">&times;</button>' +
    '<div class="count" aria-live="polite"></div>';
  document.body.appendChild(box);
  var img = box.querySelector('img');
  var count = box.querySelector('.count');

  function preload(i) {
    new Image().src = links[(i + total) % total].getAttribute('data-full');
  }

  function show(i) {
    index = (i + total) % total;
    var a = links[index];
    img.src = a.getAttribute('data-full');
    img.alt = a.querySelector('img').alt;
    count.textContent = (index + 1) + ' / ' + total;
    box.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    preload(index + 1);
    preload(index - 1);
  }

  function hide() {
    box.hidden = true;
    index = -1;
    document.documentElement.style.overflow = '';
  }

  function open(i) {
    show(i);
    history.pushState({ photo: true }, '', '#' + (index + 1));
    pushed = true;
    box.querySelector('.close').focus();
  }

  function go(step) {
    show(index + step);
    history.replaceState({ photo: true }, '', '#' + (index + 1));
  }

  function close() {
    if (pushed) {
      pushed = false;
      history.back(); // the popstate handler hides the viewer
    } else {
      hide();
      history.replaceState(null, '', location.pathname + location.search);
    }
  }

  function fromHash() {
    var n = parseInt(location.hash.slice(1), 10);
    if (n >= 1 && n <= total) show(n - 1); else hide();
  }

  links.forEach(function (a, i) {
    a.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // keep open-in-new-tab
      e.preventDefault();
      open(i);
    });
  });
  box.querySelector('.prev').addEventListener('click', function (e) { e.stopPropagation(); go(-1); });
  box.querySelector('.next').addEventListener('click', function (e) { e.stopPropagation(); go(1); });
  box.querySelector('.close').addEventListener('click', function (e) { e.stopPropagation(); close(); });
  box.addEventListener('click', function (e) { if (e.target === box) close(); });
  document.addEventListener('keydown', function (e) {
    if (box.hidden) return;
    if (e.key === 'ArrowRight') go(1);
    else if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'Escape') close();
  });
  box.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    startX = null;
    if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
  });
  window.addEventListener('popstate', function () { pushed = false; fromHash(); });
  fromHash();
})();
