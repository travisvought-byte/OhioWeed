/* Signup box.
 *
 * The page ships with a plain email fallback so it is never a dead end. When a
 * real list exists, point the box at it and the fallback is replaced:
 *
 *   EmailOctopus: put the form id on the container, e.g.
 *     <div id="signup" class="signup-box" data-eo-form="1a2b3c4d-....">
 *   Anything else (a hosted form, a Google Form, an Apps Script endpoint):
 *     put the URL in data-form-url and the box becomes a framed form.
 *
 * Nothing else on the page needs to change.
 */
(function () {
  var box = document.getElementById('signup');
  if (!box) return;

  var eo = (box.getAttribute('data-eo-form') || '').trim();
  var url = (box.getAttribute('data-form-url') || '').trim();
  if (!eo && !url) return; // keep the fallback

  box.innerHTML = '';

  if (eo) {
    // EmailOctopus renders and submits its own form, so it handles the
    // confirmation email, the unsubscribe link and the spam checks.
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://eocampaign1.com/form/' + eo + '.js';
    s.setAttribute('data-form', eo);
    box.appendChild(s);
    return;
  }

  var frame = document.createElement('iframe');
  frame.src = url;
  frame.title = 'Sign up for event email';
  frame.loading = 'lazy';
  frame.className = 'signup-frame';
  box.appendChild(frame);
})();
