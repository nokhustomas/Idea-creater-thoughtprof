// HDIBS 导航栏两级弹出菜单（hover + click 兼容）
(function () {
    var dropdowns = document.querySelectorAll('.nav-dropdown');
    dropdowns.forEach(function (dd) {
        var trigger = dd.querySelector(':scope > a');
        var level1 = dd.querySelector(':scope > .dropdown-menu');
        if (!trigger || !level1) return;

        // 点击一级触发：阻止跳转，切换显示
        trigger.addEventListener('click', function (e) {
            e.preventDefault();
            dd.classList.toggle('open');
        });

        // hover 进入一级菜单：显示二级
        var items = level1.querySelectorAll('li.has-submenu');
        items.forEach(function (item) {
            var submenu = item.querySelector(':scope > .submenu');
            if (!submenu) return;

            item.addEventListener('mouseenter', function () {
                // 关闭同级其它二级
                items.forEach(function (other) {
                    if (other !== item) other.classList.remove('open');
                });
                item.classList.add('open');
            });
            item.addEventListener('mouseleave', function () {
                item.classList.remove('open');
            });

            // 点击有二级的一级菜单：阻止跳转，切换二级
            var itemTrigger = item.querySelector(':scope > a');
            if (itemTrigger) {
                itemTrigger.addEventListener('click', function (e) {
                    e.preventDefault();
                    items.forEach(function (other) {
                        if (other !== item) other.classList.remove('open');
                    });
                    item.classList.toggle('open');
                });
            }
        });

        // 鼠标离开整个 dropdown：收起
        dd.addEventListener('mouseleave', function () {
            dd.classList.remove('open');
            items.forEach(function (item) { item.classList.remove('open'); });
        });
    });

    // 点击外部关闭
    document.addEventListener('click', function (e) {
        dropdowns.forEach(function (dd) {
            if (!dd.contains(e.target)) {
                dd.classList.remove('open');
                dd.querySelectorAll('li.has-submenu.open').forEach(function (i) {
                    i.classList.remove('open');
                });
            }
        });
    });
})();