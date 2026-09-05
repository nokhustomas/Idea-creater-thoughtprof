// 路径资源二级弹出菜单：hover/click 不跳转
(function () {
  var pathLink = document.getElementById('path-link');
  var subMenu = document.getElementById('sub-menu');
  if (!pathLink || !subMenu) return;

  // 默认阻止"路径资源"自身点击跳转，由用户选二级项
  pathLink.addEventListener('click', function (e) {
    // 仅在一级菜单已展开时不跳转；首次点击展开
    if (!subMenu.classList.contains('show')) {
      e.preventDefault();
      subMenu.classList.add('show');
    }
  });

  // hover 展开一级
  var navHasSub = pathLink.parentElement;
  navHasSub.addEventListener('mouseenter', function () {
    subMenu.classList.add('show');
  });
  navHasSub.addEventListener('mouseleave', function () {
    subMenu.classList.remove('show');
  });

  // 二级项：阻止冒泡到外层 a 的导航
  var subItems = subMenu.querySelectorAll('.sub-item');
  subItems.forEach(function (li) {
    li.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  });
})();