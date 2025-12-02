# v2 から v3 への移行ガイド

このガイドでは、ebilab v2 から v3 へのコードの移行方法を説明します。

## 概要

v3では、APIが大幅に刷新され、より直感的で宣言的な記述が可能になりました。主な変更点は以下の通りです:

- **非同期(async)ベースのライフサイクル**: すべてのライフサイクルメソッドが `async def` に
- **ライフサイクルの分割**: 単一の `steps()` から `setup()`, `steps()`, `cleanup()` の3メソッドに
- **宣言的なオプション定義**: 辞書ではなくクラス属性として定義
- **yieldベースのデータ送信**: `ctx.send_row()` から `yield` へ
- **標準ロガーの採用**: `ctx.log()` から `self.logger` へ

## 移行チェックリスト

- [ ] インポートの更新
- [ ] 基底クラス名の変更
- [ ] オプション定義の変更
- [ ] ライフサイクルメソッドの分割と非同期化
- [ ] データ送信方法の変更
- [ ] ログ出力方法の変更
- [ ] Plotterの更新
- [ ] 起動関数の変更

## インポートの変更

### v2

```python
from ebilab.experiment import (
    ExperimentProtocol,
    ExperimentPlotter,
    ExperimentContext,
    PlotterContext,
    launch_experiment,
    ExperimentProtocolGroup,
)
from ebilab.experiment.options import FloatField, SelectField
from ebilab.experiment.devices import K34411A
```

### v3

```python
import asyncio
from ebilab.api import BaseExperiment, BasePlotter, FloatField, SelectField
from ebilab.gui.controller import launch_gui
from ebilab.visa import K34411A
```

**変更点:**

| v2 | v3 |
|----|----|
| `ExperimentProtocol` | `BaseExperiment` |
| `ExperimentPlotter` | `BasePlotter` |
| `launch_experiment()` | `launch_gui()` |
| `ebilab.experiment.options` | `ebilab.api` |
| `ebilab.experiment.devices` | `ebilab.visa` |

## Experimentクラスの変更

### v2

```python
class RandomWalkExperiment(ExperimentProtocol):
    columns = ["v", "v2"]
    name = "random-walk"

    options = {
        "initial": FloatField(default=2),
        "step": SelectField(choices=[1, 2, 4], default_index=1),
    }

    def steps(self, ctx: ExperimentContext) -> None:
        v = ctx.options["initial"]
        step = ctx.options["step"]
        while True:
            ctx.log(f"log: {v}")
            ctx.send_row({"v": v, "v2": v * 2})
            time.sleep(0.2)
            v += step if random.random() < 0.5 else -step
            ctx.loop()
```

### v3

```python
class RandomWalkExperiment(BaseExperiment):
    columns = ["v", "v2"]
    name = "random-walk"

    # オプションはクラス属性として定義
    initial = FloatField(default=2.0)
    step = SelectField(choices=[1, 2, 4], default_index=1)

    async def setup(self):
        # 実験開始前の初期化処理
        self.v = self.initial
        self.logger.info(f"Initial value: {self.v}")

    async def steps(self):
        while True:
            self.logger.debug(f"log: {self.v}")

            # yieldでデータを送信
            yield {"v": self.v, "v2": self.v * 2}

            # asyncio.sleepを使用
            await asyncio.sleep(0.2)

            self.v += self.step if random.random() < 0.5 else -self.step
            # ctx.loop() は不要

    async def cleanup(self):
        # 正常終了・中断・エラー時に必ず呼ばれる
        self.logger.info("Experiment finished")
```

**主な変更点:**

1. **オプション定義**: 辞書 `options = {...}` → クラス属性 `initial = FloatField(...)`
2. **オプションへのアクセス**: `ctx.options["initial"]` → `self.initial`
3. **ライフサイクル**: 単一の `steps(ctx)` → 3つのメソッド `setup()`, `steps()`, `cleanup()`
4. **非同期化**: すべてのメソッドが `async def`
5. **データ送信**: `ctx.send_row({...})` → `yield {...}`
6. **ログ出力**: `ctx.log()` → `self.logger.info()` / `self.logger.debug()` など
7. **スリープ**: `time.sleep()` → `await asyncio.sleep()`
8. **ループ制御**: `ctx.loop()` の呼び出しが不要に

## Plotterクラスの変更

### v2

```python
@RandomWalkExperiment.register_plotter
class HistgramPlotter(ExperimentPlotter):
    name = "histgram"

    options = {
        "bins": FloatField(default=10),
    }

    def prepare(self, ctx: PlotterContext):
        self._ax = self.fig.add_subplot(111)

    def update(self, df, ctx: PlotterContext):
        self._ax.cla()
        self._ax.hist(df["v"], bins=int(ctx.plotter_options["bins"]))
```

### v3

```python
@RandomWalkExperiment.register_plotter
class HistgramPlotter(BasePlotter):
    name = "histgram"

    # オプションはクラス属性として定義
    bins = FloatField(default=10.0)

    def setup(self):
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        if hasattr(self, "_ax") and not df.empty:
            self._ax.clear()
            self._ax.hist(df["v"], bins=int(self.bins))

            # 実験インスタンスへのアクセス
            if self.experiment:
                self._ax.set_title(f"step={self.experiment.step}")
```

**主な変更点:**

1. **基底クラス**: `ExperimentPlotter` → `BasePlotter`
2. **オプション定義**: 辞書 → クラス属性
3. **初期化メソッド**: `prepare(ctx)` → `setup()` (引数なし)
4. **更新メソッド**: `update(df, ctx)` → `update(df)` (ctxなし)
5. **オプションへのアクセス**: `ctx.plotter_options["bins"]` → `self.bins`
6. **実験インスタンスへのアクセス**: `self.experiment` で実験パラメータにアクセス可能
7. **実行状態の確認**: `self.experiment.is_running` で実験中かどうかを判定可能

## 起動関数の変更

### v2

```python
if __name__ == "__main__":
    launch_experiment([
        RandomWalkExperiment,
        ExperimentProtocolGroup(name="dir", protocols=[NothingExperiment]),
    ])
```

### v3

```python
if __name__ == "__main__":
    launch_gui([RandomWalkExperiment])
```

**変更点:**

- `launch_experiment()` → `launch_gui()`
- `ExperimentProtocolGroup` によるグルーピング機能は削除されました

## v3の新機能

### 実験インスタンスへのアクセス

Plotterから `self.experiment` で実験インスタンスにアクセスできます:

```python
def update(self, df):
    # 実験パラメータへのアクセス
    step = self.experiment.step
    initial = self.experiment.initial

    # 実験中かどうかの判定
    if self.experiment.is_running:
        # 実験中のみの処理
        pass
```

### ログレベル

`self.logger` は Python 標準の logger で、複数のログレベルをサポートします:

```python
self.logger.debug("詳細なデバッグ情報")
self.logger.info("一般的な情報")
self.logger.warning("警告")
self.logger.error("エラー")
self.logger.exception("例外情報とトレースバック")
```

### 自動追加される列

データには以下の列が自動で追加されます:

- `t`: 実験開始からの経過時間（秒）
- `time`: ISO形式のタイムスタンプ
- `sync_t`: 最後のsyncボタン押下からの経過時間

### デバッグモード

GUIからデバッグ実行を選択すると、データを保存せずに実験を実行できます。

### sync機能

実験中にsyncボタン（またはF12キー）を押すと、そのタイムスタンプが記録されます。

### VISAデバイスのアドレス指定

複数のデバイスを接続する場合など、アドレスを明示的に指定できます:

```python
multimeter = K34411A(addr="GPIB0::22::INSTR")
```

## 完全な移行例

### v2 コード

```python
import time
import random

from ebilab.experiment import (
    ExperimentProtocol, ExperimentPlotter,
    ExperimentContext, PlotterContext, launch_experiment
)
from ebilab.experiment.options import FloatField, SelectField
from ebilab.experiment.devices import K34411A


class MyExperiment(ExperimentProtocol):
    columns = ["value"]
    name = "my-exp"

    options = {
        "param": FloatField(default=1.0),
    }

    def steps(self, ctx: ExperimentContext) -> None:
        multimeter = K34411A()
        param = ctx.options["param"]
        ctx.log("Experiment started")

        while True:
            value = multimeter.measure_voltage() * param
            ctx.send_row({"value": value})
            ctx.log(f"Value: {value}")
            time.sleep(0.1)
            ctx.loop()


@MyExperiment.register_plotter
class MyPlotter(ExperimentPlotter):
    name = "plot"

    def prepare(self, ctx: PlotterContext):
        self._ax = self.fig.add_subplot(111)

    def update(self, df, ctx: PlotterContext):
        self._ax.cla()
        self._ax.plot(df["t"], df["value"])


if __name__ == "__main__":
    launch_experiment([MyExperiment])
```

### v3 コード

```python
import asyncio

from ebilab.api import BaseExperiment, BasePlotter, FloatField
from ebilab.gui.controller import launch_gui
from ebilab.visa import K34411A


class MyExperiment(BaseExperiment):
    columns = ["value"]
    name = "my-exp"

    param = FloatField(default=1.0)

    async def setup(self):
        self.multimeter = K34411A()
        self.logger.info("Experiment started")

    async def steps(self):
        while True:
            value = self.multimeter.measure_voltage() * self.param
            yield {"value": value}
            self.logger.info(f"Value: {value}")
            await asyncio.sleep(0.1)

    async def cleanup(self):
        self.logger.info("Experiment finished")


@MyExperiment.register_plotter
class MyPlotter(BasePlotter):
    name = "plot"

    def setup(self):
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        if hasattr(self, "_ax") and not df.empty:
            self._ax.clear()
            self._ax.plot(df["t"], df["value"])


if __name__ == "__main__":
    launch_gui([MyExperiment])
```

## 参照

- [v3.0.0 pre リリースノート](changelog-v3.0.0-pre.md)
- [サンプルコード](https://github.com/ebiyu/ebilab/tree/main/sample)
