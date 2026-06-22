## Google Play がcrashする問題を直したバージョン

PIFを適用していると、Google PlayとWalletがクラッシュする問題があった。
Minikin(フォントローダー?)の不具合と思われ、null dereferenceでSIGSEGVで落ちていた。

以下の2ファイルをモジュール側に追加することとした:

```text
system/fonts/NotoSansCJK-Regular.ttc
system/fonts/NotoSerifCJK-Regular.ttc
```

中身は McMejiro-Regular を 4 index 分入れた TTC。stock 側にも同名ファイルが存在するため、namespace ごとの挙動は以下になる。

- 通常 namespace: Magisk overlay の `NotoSansCJK-Regular.ttc` / `NotoSerifCJK-Regular.ttc` が見えるため McMejiro が使われる
- PIF 隔離 namespace: overlay が剥がれても stock の同名 CJK TTC が見えるため、ファイル open が null にならずクラッシュしない

つまり、PIF 隔離対象では McMejiro 表示を諦めて stock Noto CJK にフォールバックし、クラッシュを避ける設計。

Android17 QPR1 on Pixel 10a (CP21.260330.011) での動作を確認した。

---

### 以下オリジナルのREADME:

#### McMejiro Font

McMejiro font patch for Japanese users.
Tested on Google Pixel 6 Pro (Android 12).

#### NOTICE

* You should use latest Magisk Manager to install this module. If you meet any problem under installation from Magisk Manager, please try to install it from recovery.

## License

- This module is licensed under [WTFPL](http://www.wtfpl.net/).

```
            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
                    Version 2, December 2004

 Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>

 Everyone is permitted to copy and distribute verbatim or modified
 copies of this license document, and changing it is allowed as long
 as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.
```
