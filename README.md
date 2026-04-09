# Tetris

这个仓库现在提供两个版本：

## 1) 手机浏览器版（HTML5）

- 文件：`index.html` + `styles.css` + `tetris.js`
- 特点：
  - 触屏按钮、移动端布局、浏览器即开即玩
  - 连击系统（Combo）
  - 幽灵落点（Ghost Piece）
  - 清行闪光 + 屏幕震动 + 文本特效
  - 轻量 WebAudio 音效（移动/旋转/消行/硬降）
  - 暂停/继续、重开、实时速度倍率调节（0.6x~1.8x）

运行方式：

```bash
python3 -m http.server 8000
```

然后访问 `http://localhost:8000`（手机可通过同局域网 IP 访问）。

网页控制补充：

- 点击「开始/继续」恢复游戏
- 点击「暂停」或键盘 `P` 切换暂停
- 键盘 `Enter` 快速继续
- 使用速度滑条实时调节下落倍率

## 2) 数学+物理增强版（Pygame + Pymunk）

- 文件：`tetris_physics.py`
- 特点：
  - 弹簧阻尼驱动的果冻方块形变
  - 硬降/落地冲击反馈
  - 三阶段消行动画（压缩、失稳、碎块）
  - Pymunk 物理碎块粒子效果
  - 固定子步进（fixed-step）物理更新，更稳的模拟表现

安装依赖：

```bash
pip install -r requirements.txt
```

运行：

```bash
python3 tetris_physics.py
```

控制：

- ← →：移动
- ↑：旋转
- ↓：软降
- 空格：硬降
- ESC：暂停/继续
- F1：重新开始
