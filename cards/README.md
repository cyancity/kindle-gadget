# cards/

卡片 HTML 源目录（PC 侧渲染成 PNG 后推送上屏）。

- `hello.html`：最小示例卡，`python push.py cards/hello.html` 直接可用
- `usage.html` 及 `versions/`：由 `usage_card.py` 和 Studio 生成（含本机真实用量数据），不入库
- 新卡片：Studio 里「+新建」，或复制 hello.html 改

约束（渲染链）：1264x1680 固定尺寸、无 flex gap/sticky/动画、字号 >=30px、字体用系统字体栈；
横屏卡片 1680x1264，推送时 `python push.py <file> --orientation landscape`。
