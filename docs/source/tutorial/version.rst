####################
バージョンについて
####################

このライブラリは随時アップデートしています。
バージョンは :code:`a.b.c` の形式で定義され、v2.7.0以降は以下のポリシーで更新されます。

* a (Major version): メソッドの仕様変更や機能の削除など、破壊的な変更があった場合に更新されます。
* b (Minor version): 新機能の追加や非公開APIの変更の際に更新されます。
* c (Patch version): バグ修正や非公開APIの変更など、機能に変更がない修正の際に更新されます。

なお、ドキュメントに未完成(unstable)と明記されている機能に関しては、パッチバージョンで更新が行なわれることがあります。

v2.6.0以前は以下のポリシーで更新されました。

* a (Major version): 重要で破壊的な変更があった場合に更新されます。
* b (Minor version): 新機能の追加や一部機能の仕様な変更など、軽微な変更があった場合に更新されます。
* c (Patch version): 新メソッドの追加などの軽微な機能や、バグ修正など機能に変更がない場合に更新されます。ドキュメントに未完成(unstable)と明記されている機能に関しては、パッチバージョンで更新が行なわれることがあります。

****************************************
実験の再現性のために
****************************************

:code:`ebilab` のバージョンを更新した場合、過去の実験コードの動作が変化し、実験を再現できなくなる可能性があります。それを防止するには、何らかの方法でバージョンを固定することを推奨します。

minor versionやpatch versionに関しては後方互換性がありますが、バグに依存していた場合や内部機能をハックしていた場合にはその限りではありません。

代表的なものとしては :code:`venv` や :code:`pipenv` などが挙げられます。

.. 一方で、そのようなツールの使用に慣れていない場合や、たった1ファイルのスクリプトなど仮想環境を導入するのが煩雑だと感じる場合もあるでしょう。
.. その場合では、 :py:func:`assert_ebilab_version() <ebilab.assert_ebilab_version>` 関数を用いて簡易的にバージョンのチェックを行なうことができます。

.. 例えば、以下のようなコードを実験コードの最上部に記述してください。

.. .. code-block:: python

..     from ebilab import assert_ebilab_version
..     assert_ebilab_version("1") # Fix major version

.. もしインストールされている :code:`ebilab` のバージョンが指定したものと一致しなかった場合は、 :py:class:`VersionDidNotMatch <ebilab.VersionDidNotMatch>` が送出されます。

.. その場合は該当するバージョン手動でをインストールする必要があります。このように、簡易的な動作保証のチェックとして利用することができます。

.. .. note::

..     基本的にはメジャーバージョンのみの指定で十分ですが、ドキュメントに記載されていないクラスを利用している場合などはそれ以上の指定が有効となる場合があります。
..     厳密にバージョンを指定したい場合は、以下のような構文を利用することができます。

..     .. code-block:: python

..         from ebilab import assert_ebilab_version
..         assert_ebilab_version("1.0") # Fix minor version

..     .. code-block:: python

..         from ebilab import assert_ebilab_version
..         assert_ebilab_version("1.0.0") # Fix patch version


