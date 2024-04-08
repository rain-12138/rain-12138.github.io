// JavaScript 代码

// 例如，可以在这里添加一个功能，让导航栏在滚动时变为固定

const nav = document.querySelector('header');

window.addEventListener('scroll', () => {
  if (window.scrollY > 0) {
    nav.classList.add('fixed');
  } else {
    nav.classList.remove('fixed');
  }
});