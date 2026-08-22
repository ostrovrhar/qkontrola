# Validacija podatkov - format CSV

## Namen

Datoteka CSV definira nepogojna pravila za preverjanje vrednosti atributov QGIS
slojev. Pravila veljajo za vse objekte v sloju.

Pogojna pravila med atributi so opisana v `VALIDACIJA_RELACIJ.md`.

## Struktura stolpcev

```csv
TARGET_FIELD,TARGET_FIELD_RULE,TARGET_FIELD_RULE_PARAM,TARGET_FIELD_TYPE
```

| Stolpec | Pomen |
|---|---|
| `TARGET_FIELD` | Atribut, ki se preverja. |
| `TARGET_FIELD_RULE` | Pravilo, ki mora veljati za `TARGET_FIELD`. |
| `TARGET_FIELD_RULE_PARAM` | Parameter pravila. |
| `TARGET_FIELD_TYPE` | Pričakovani tip polja v sloju. Stolpec je lahko prazen. |

Vrstica se preskoči, če se vrednost v stolpcu `TARGET_FIELD` začne z `;`. To se
uporablja za komentarje in ločevanje sklopov pravil.

## Kaj format omogoča

- preverjanje dovoljenih vrednosti atributa
- preverjanje z regularnim izrazom
- preverjanje, da polje ni prazno
- preverjanje, da je polje prazno
- preverjanje tipa polja v sloju
- komentarje v CSV datoteki
- delne specifikacije: atributi brez pravila se ne preverjajo

## Pravila

| `TARGET_FIELD_RULE` | Pomen |
|---|---|
| `dovoljene vrednosti` | `TARGET_FIELD` mora biti ena od vrednosti v `TARGET_FIELD_RULE_PARAM`. |
| `regex` | `TARGET_FIELD` se mora ujemati z regularnim izrazom v `TARGET_FIELD_RULE_PARAM`. |
| `ne sme biti prazno` | `TARGET_FIELD` ne sme biti prazen. |
| `mora biti prazno` | `TARGET_FIELD` mora biti prazen. |

Prazna vrednost pomeni `NULL` ali prazen niz. Pri pravilih `ne sme biti prazno` in
`mora biti prazno` lahko `TARGET_FIELD_RULE_PARAM` vsebuje dodatne vrednosti, ki se
štejejo kot prazne. Vrednosti so ločene z `|`.

Primer:

```csv
negovan,ne sme biti prazno,Ni vrednosti,String
zasnova,mora biti prazno,Ni vrednosti,String
```

Pri prvem pravilu sta prazna vrednost in `Ni vrednosti` neveljavni. Pri drugem
pravilu so prazna vrednost in `Ni vrednosti` veljavne, druge vrednosti pa ne.

## Dovoljene vrednosti

Vrednosti v `TARGET_FIELD_RULE_PARAM` so ločene z `|`.

```csv
OS,dovoljene vrednosti,1|2,Integer
```

Prazna vrednost je dovoljena samo, če je med dovoljenimi vrednostmi navedeno
`prazno`.

```csv
GEOG_IME,dovoljene vrednosti,crke|0000|8888|prazno,String
```

Podprte so tudi posebne oznake.

| Oznaka | Pomen |
|---|---|
| `regex(...)` | Regularni izraz kot dovoljena vrednost. |
| `zN-` | Predponsko ujemanje z vrednostjo `N-`. |
| `********` | Točno 8 števk. |
| `crke`, `črke` | Besedilo po vzorcu `^[A-ZČŠŽ][A-Za-zČŠŽčšž ]{1,}$`. |
| `stevilke`, `številke` | Celo ali decimalno število po vzorcu `^[-]?[0-9]+([.][0-9]+)?$`. |
| `crke_i`, `črke_i` | Besedilo po vzorcu `^[A-Za-zČŠŽčšž][A-Za-zČŠŽčšž ]{1,}$` (prvi znak ni nujno velik). |
| `brez_stevilk`, `brez_številk` | Besedilo brez številk, vzorec `^[^0-9]+$`. |
| `prvi_znak_ni_stevilka`, `prvi_znak_ni_številka` | Prvi znak ni številka, vzorec `^[^0-9].*$`. |
| `prazno` | Dovoli `NULL` ali prazen niz. |

### Podrobnosti posameznih oznak

#### `crke`, `črke`

- Prvi znak mora biti velika črka (`A-ZČŠŽ`).
- Sledi vsaj en znak iz nabora: črke (velike in male, vključno s slovenskimi šumniki)
  in presledki.
- Enoznakovni niz ne ustreza: `A` ni veljavno, `AB` je veljavno.
- Ne dovoljuje številk, oklepajev, pik, vejic, vezajev, poševnic ali drugih ločil.
- Primeri veljavnih vrednosti: `Gozd`, `Mladovje`, `Drobna voda`.
- Primeri neveljavnih vrednosti: `RAZNOMERNO (PS-ŠP, PREB)` (oklepaji, vezaj,
  vejica), `1A` (številka), `A` (en znak), `Lesna-zaloga` (vezaj).

#### `stevilke`, `številke`

- Cela ali decimalna števila.
- Decimalno ločilo je pika, ne vejica.
- Dovoljen je začetni minus.
- Ni dovoljen znak `+`, ločilo tisočic ali eksponentni zapis.
- Primeri veljavnih vrednosti: `42`, `-3`, `12.5`.
- Primeri neveljavnih vrednosti: `1.234,5` (vejica namesto pike), `+7` (znak `+`),
  `1e2` (eksponent).

#### `********`

- Natanko 8 števk, nič manj, nič več.
- Ni poljuben maskirni vzorec in ne pomeni "osem poljubnih znakov".
- Primeri veljavnih vrednosti: `20140702`, `12345678`.
- Primeri neveljavnih vrednosti: `2014070` (7 števk), `201407021` (9 števk),
  `ABCD1234` (črke), `2014-0702` (vezaj).

#### `regex(...)`

- Regularni izraz je naveden v oklepaju, npr. `regex(^[0-9]{8})`.
- Ujemanje poteka od začetka niza (`re.match`). `regex(^[0-9]{8})` se ujema tudi
  z vrednostjo `20140702.0000000`, ker se začetek niza ujema z vzorcem.
- Če je zahtevano ujemanje celotnega niza, uporabite `^` na začetku in `$` na
  koncu izraza, npr. `regex(^[0-9]{8}$)`.

#### `zN-`

- Predpona v obliki `zN-`, kjer je `N` poljuben niz.
- Ujemanje: vrednost atributa se začne z `N-`.
- Primer: `z1-` v parametru pomeni, da se veljavne vrednosti začnejo z `1-`
  (npr. `1-234`, `1-ABC`).
- Uporabno za hierarhične kode.

#### `prazno`

- Pri pravilu `dovoljene vrednosti` izrecno dovoli `NULL` ali prazen niz.
- Uporabno v kombinaciji z drugimi vrednostmi, npr. `crke|prazno`.

#### `crke_i`, `črke_i`

- Enako kot `crke`, le da je prvi znak lahko velika ali mala črka.
- Vzorec: `^[A-Za-zČŠŽčšž][A-Za-zČŠŽčšž ]{1,}$`.
- Ostale omejitve so enake: dovoljene so samo črke in presledki, brez številk in ločil.
- Primeri veljavnih vrednosti: `Gozd`, `gozd`, `Mladovje`, `drobna voda`.
- Primeri neveljavnih vrednosti: `RAZNOMERNO (PS-ŠP, PREB)` (oklepaji, vezaj,
  vejica), `1A` (številka), `A` (en znak), `Lesna-zaloga` (vezaj).

#### `brez_stevilk`, `brez_številk`

- Vrednost ne sme vsebovati nobene številke.
- Vzorec: `^[^0-9]+$`.
- Dovoljeni so vsi znaki razen številk: črke, presledki, oklepaji, vejice, vezaji,
  pike, poševnice, dvopičja itd.
- Vrednost mora vsebovati vsaj en znak.
- Primeri veljavnih vrednosti: `RAZNOMERNO (PS-ŠP, PREB)`, `Lesna-zaloga`,
  `Grmičav gozd`, `---`, `()`.
- Primeri neveljavnih vrednosti: `Razred 1` (vsebuje številko), `1A`, `123`.
- Opozorilo: oznaka ne preverja smiselnosti besedila. Vrednosti kot `---` ali `()`
  so veljavne, ker ne vsebujejo številk. Namenjena je predvsem poljem, kjer so
  opisne vrednosti z ločili in številke v njih niso smiselne.

#### `prvi_znak_ni_stevilka`, `prvi_znak_ni_številka`

- Prvi znak ne sme biti številka, številke so dovoljene kasneje.
- Vzorec: `^[^0-9].*$`.
- Vrednost mora vsebovati vsaj en znak.
- Primeri veljavnih vrednosti: `Razred 1`, `RAZNOMERNO (PS-ŠP, PREB)`,
  `Lesna-zaloga`, `a123`, `()`, `A`.
- Primeri neveljavnih vrednosti: `1. razred` (prvi znak je številka), `123`.

Primer predponskega ujemanja:

```csv
VODE_ID,dovoljene vrednosti,1|z1-|2|z2-|0000|9999,String
```

Vrednost `z1-` pomeni, da se vrednost atributa začne z `1-`.

## Regex

Pravilo `regex` uporablja regularni izraz iz `TARGET_FIELD_RULE_PARAM`.

```csv
DVIR,regex,^[0-9]{8},Double
```

Prazna vrednost pri pravilu `regex` ni veljavna.

## Tip polja

`TARGET_FIELD_TYPE` je neobvezen. Če je prazen, se tip polja ne preverja.

Podprti normalizirani tipi:

| Zapis v CSV | Tip QGIS |
|---|---|
| `Integer`, `Int` | celo število |
| `Double`, `Real` | decimalno število |
| `String`, `Text` | niz |
| `Date` | datum |
| `DateTime` | datum in čas |
| `Boolean`, `Bool` | logična vrednost |

Napaka tipa se zabeleži kot napaka sheme in ni vezana na posamezen objekt.

## Velike in male črke

Primerjava literalnih vrednosti je dobesedna (case-sensitive). `PANJEVEC` ni enako `panjevec`,
`Ni vrednosti` ni enako `NI VREDNOSTI`.

Imena atributov v CSV morajo biti zapisana enako kot v sloju.

Regularni izrazi uporabljajo običajno občutljivost na velike in male črke, razen če
je v izrazu določeno drugače.

## Primer

```csv
TARGET_FIELD,TARGET_FIELD_RULE,TARGET_FIELD_RULE_PARAM,TARGET_FIELD_TYPE
VRSTA,dovoljene vrednosti,1|2|3|4,Integer
OS,dovoljene vrednosti,1|2,Integer
GEOG_IME,dovoljene vrednosti,crke|0000|8888|prazno,String
DVIR,regex,^[0-9]{8},Double
negovan,ne sme biti prazno,Ni vrednosti,String
zasnova,mora biti prazno,Ni vrednosti,String
```
