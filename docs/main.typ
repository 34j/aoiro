= 青色申告

== 概要

#figure(image("保存期間.png"), caption: [#cite(<kichou_2025>, supplement: "p.9")])

- 青色申告で提出する書類は@kessansyo_2025 のみであり、その他の帳簿は提出しないが、保管しておく必要がある。
- @kessansyo_kakikata_2025 は@kessansyo_2025 の書き方を解説する簡易な文書である。
- @tebiki_kessan_2025, @tebiki_chinnsyakutaisyou_2025, @kichou_2025 は提出不要な帳簿・書類の書き方を説明するもので、内容が似通っているようないないような感じがあるが、 @kichou_2025 はおそらくやわからい資料で、@tebiki_2025, @tebiki_chinnsyakutaisyou_2025 はセットでかたい資料のような感じがある。
- 仕訳帳以外の帳簿・決算関係書類は、仕訳帳から自動的に生成できる。

== 定式化

#let data = yaml("../src/aoiro/account.yml")
#let accounting = $"勘定科目"$
#let assets = $"資産"$
#let liabilities = $"負債"$
#let netassets = $"純資産"$
#let profit = $"収益"$
#let loss = $"費用"$
#let journalitem = $"仕訳要素"$
#let journalitems = $"仕訳要素集合"$
#let journalline = $"単一仕訳"$
#let journalmultiline = $"複合仕訳"$
#let journal = $"単一仕訳帳"$
#let journalmulti = $"複合仕訳帳"$
#let decompmin = $op("DecompMin")$
#let decompsundry = $op("DecompSundry")$

#let date = $"Date"$

#let mkset(key1) = {
    let d = data.at(key1).pairs().filter(x => x.at(0) != "追加").map(x => x.at(1)).flatten()
    [${$#d.join($,$)$}$]
}


- 勘定科目は@kessansyo_2025 に記載されているもののみを使用する。適当に追加することも可能である。
- (勘定科目)
    - $assets := $#mkset("資産")
    - $liabilities := $#mkset("負債")
    - $netassets :=$#mkset("純資産")
    - $profit := $#mkset("収益")
    - $loss := $#mkset("費用")
    - $accounting := assets union liabilities union netassets union profit union loss union {"諸口"}$
- (勘定科目の全順序)$accounting$に適当な全順序$<$を導入する。
- (仕訳要素)$journalitem := accounting times NN$
//- (仕訳要素集合)$journalitems := {x in 2^journalitem | 0 < abs(x) < infinity}$
- (単一仕訳)$journalline := date times {v_1 = v_2 | ((d, v_1), (d, v_2)) in journalitem^2}$
- (可能な勘定科目の組)ほとんどの組み合わせが可能であるため、本定式化では可能な勘定科目の組み合わせを考えないものとする。
#table(columns: 6, rows: 6,
"借方/貸方", "資産", "負債", "純資産", "収益", "費用",
"資産", "当座預金/普通預金", "当座預金/借入金", "当座預金/資本金", "当座預金/売上", "(逆仕訳)",
"負債", "買掛金/当座預金", "買掛金/支払手形", "買掛金/資本金?", "前受金/売上(相殺)", "(逆仕訳)",
"純資産", "(逆仕訳)", "(逆仕訳)", "繰越利益剰余金/利益準備金", "✗(損益を経由)", "✗(損益を経由)",
"収益", "(逆仕訳)", "(逆仕訳)", "✗(損益を経由)", "相殺(物々交換)", [相殺・修正(勘定科目変更) #cite(<ayamari_2025>, supplement: "p.29")],
"費用", "仕入/当座預金", "仕入/買掛金", "✗(損益を経由)", "相殺・修正", "相殺"
)
- (複合仕訳)$journalmultiline := date times {0 < abs(I) < infinity and 0 < abs(J) < infinity and sum_i v_i = sum_j v'_j | ({(d_i, v_i) | i in I}, {(c_j, v'_j) | j in J}) in (2^journalitem)^2}$
- (複合仕訳の最小の分解)
  - $forall ({(d_i, v_i) | i in I}, {(c_j, v'_j) | j in J}) in journalmultiline. exists {((d''_k, v''_k), (c''_k, v''_k)) | k in K} in 2^journalline. (forall a in accounting. sum_i 1_(c_(i) = a) v_i = sum_k 1_(c''_k = a) v''_k and sum_j 1_(c_(j) = a) v'_j = sum_k 1_(c''_k = a) v''_k)$
  - $decompmin$: このような$2^journalline$で要素数が最小のものを返す関数は同型でない
- (複合仕訳の諸口による分解)
  - $forall ({(d_i, v_i) | i in I}, {(c_j, v'_j) | j in J}) in journalmultiline. exists {((d''_k, v''_k), (c''_k, v''_k)) | k in K, (d''_k = "諸口") or (c''_k = "諸口")} in 2^journalline. (forall i in I. sum_i' 1_(c_(i') = c_i) v_i = sum_k 1_(c''_k = c_i) v''_k) and (forall j in J. sum_j' 1_(c_(j') = c_j) v'_j = sum_k 1_(c''_k = c_j) v''_k)$
  - $decompsundry$: このような$2^journalline$で要素数が最小のものを返す関数は同型
- (単一仕訳帳)$journal := {abs(J) < infinity | J in 2^journal}$
- (複合仕訳帳)$journalmultiline := {abs(J) < infinity | J in 2^journalmultiline}$
- (仕訳帳の性質)$forall {J_i | i in I} in journal. sum_i$

#bibliography("main.bib")
