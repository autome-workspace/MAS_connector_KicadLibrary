# MAS_connector_KicadLibrary
ここは、MAS規格で規定されるコネクタのシンボル、フットプリントを管理するライブラリである。
  
MAS規格で規定されないコネクタ、ICなどはここには含めないこと。  
シンボルには各ピンの用途、電圧を明記する。  
また各シンボルには適合するフットプリントを１つ以上登録すること。

## PCMからのインストール（配布準備中）

KiCadの「プラグイン＆コンテンツマネージャー（PCM）」向けに、
シンボルとフットプリントをまとめたライブラリパッケージを配布する。
対応対象はKiCad 10.0以降。Pythonプラグインの実装は不要。

公開後はPCMの「リポジトリを管理」に配布用の `repository.json` のURLを
一度追加し、「ライブラリ」からインストールする。
標準設定ではシンボルとフットプリントが `PCM_MAS_V3` として自動登録される。
「パッケージと更新」のライブラリ自動登録を有効にし、
ライブラリ名の接頭辞は標準の `PCM_` を使用する。
KiCad標準の `Connector_JST` と `Connector_AMASS` も必要。

ZIPをダウンロードし、PCMの「ファイルからインストール」を使うこともできる。
GitHubの「Source code (zip)」はPCMパッケージとしては使えない。
現時点では配布用URL・インストール用ZIPは未公開。

## 配布パッケージの生成

Python 3.9以降を使用する。参照の検査のみを行う場合：

```powershell
python tools/build_pcm.py --check
```

配布前に以下を解決する必要がある。

- ライセンスと、外部から取り込んだデータの再配布条件を確定する。
- 3Dモデルは未収録で、参照は個人PCの絶対パスになっている。
  現在の生成ツールは `--without-3d` を指定した場合に限り、配布ZIP内の3D参照を削除する。

権利者が決定したライセンスを指定して生成する。
次のURLとライセンス文字列は、実際の公開先・決定した条件に置き換える。

```powershell
python tools/build_pcm.py --version 0.1.0 --license "DECIDED-LICENSE" --without-3d --base-url "https://github.com/autome-workspace/MAS_connector_KicadLibrary/releases/download/v0.1.0"
```

`dist/0.1.0/` に以下を生成する。参照に不備がある場合は生成を中止する。

- `mas-connectors-0.1.0.zip`：PCMからインストールするライブラリ本体
- `packages.json`：バージョン・ダウンロードURL・SHA-256
- `repository.json`：PCMに追加するリポジトリ情報

3ファイルを同じGitHub Releaseにアップロードする。
利用者に案内するリポジトリURLは、最新Releaseを参照する
`https://github.com/autome-workspace/MAS_connector_KicadLibrary/releases/latest/download/repository.json`
とする。各バージョンのファイルを公開した後、最新Releaseを切り替える。
現在の生成ツールは最新版1件を掲載するため、旧版の一覧は保持しない。

生成時だけシンボルの自作フットプリント参照を `PCM_MAS_V3:` に変換し、
標準ライブラリへの参照は保持する。元のライブラリファイルは書き換えない。
初期パッケージの状態は `testing`。公開前に別のKiCad環境でPCMからの導入と
シンボルからのフットプリント割り当てを確認する。

仕様：
[KiCad Addons](https://dev-docs.kicad.org/en/addons/index.html)、
[KiCad PCM](https://docs.kicad.org/10.0/en/kicad/kicad.html#plugin-and-content-manager)

## 修正したフットプリント参照

`JST_XH_2P`・`JST_XH_3P`・`JST_XH_4P` は、KiCad標準の
`Connector_JST:JST_XH_S{2,3,4}B-XH-A_1x0{2,3,4}_P2.50mm_Horizontal`
を使用する。シンボル名に合わせてXHシリーズの横向きタイプを選定し、
以前のXA・PAシリーズの参照と検索キーワードを修正した。
各部品は2.5 mmピッチ、パッド番号は1から極数まで。
[JST XHデータシート](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf)

`RJ45` は指定型番を維持し、既存の `Y.maku` リポジトリ内の
`kicad/_Setting/JLCImport/JLCImport.pretty/HC-WK88-H16-QS.kicad_mod`
から同名ファイルを `MAS_V3.pretty` に収録した。
パッドの番号・座標・穴径は元データを保持し、未同梱の3Dモデルへの絶対パス参照だけ削除した。
この取り込みは新たなライセンスを付与するものではなく、配布条件は公開前に確定する。
