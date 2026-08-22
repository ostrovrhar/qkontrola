# Validacija relacij - format CSV

## Namen

Datoteka CSV definira pogojna pravila za preverjanje atributov QGIS slojev.
Pravilo se izvede samo za objekte, pri katerih ima `CONDITION_FIELD` eno od
vrednosti iz `CONDITION_FIELD_VALUE`.

Format je namenjen validaciji relacij med atributi. Nepogojna validacija vrednosti
atributov je opisana v `VALIDACIJA_PODATKOV.md`.

## Struktura stolpcev

```csv
TARGET_FIELD,TARGET_FIELD_RULE,TARGET_FIELD_RULE_PARAM,CONDITION_FIELD,CONDITION_FIELD_VALUE
```

| Stolpec | Pomen |
|---|---|
| `TARGET_FIELD` | Atribut, ki se preverja. |
| `TARGET_FIELD_RULE` | Pravilo, ki mora veljati za `TARGET_FIELD`. |
| `TARGET_FIELD_RULE_PARAM` | Parameter pravila. |
| `CONDITION_FIELD` | Atribut, ki določa, ali se pravilo izvede. |
| `CONDITION_FIELD_VALUE` | Vrednost ali seznam vrednosti, ki sprožijo pravilo. |

Vrstica se preskoči, če se vrednost v stolpcu `TARGET_FIELD` začne z `;`. To se
uporablja za komentarje in ločevanje sklopov pravil.

## Kaj format omogoča

- pogojno preverjanje enega atributa glede na vrednost drugega atributa
- več pogojnih vrednosti v eni vrstici z ločilom `|`
- negacijo pogoja z znakom `¬` na začetku vrednosti
- pravila `dovoljene vrednosti`, `regex`, `ne sme biti prazno` in `mora biti prazno`
- ločene vrstice za zahtevo, da mora biti polje izpolnjeno, in zahtevo, da mora biti prazno
- delne specifikacije: kombinacije, ki niso zapisane v CSV, se ne preverjajo

Format ne sklepa komplementarnih pravil. Vrstica `ne sme biti prazno` ne pomeni,
da mora biti polje za vse druge pogoje prazno. Za to mora obstajati ločena vrstica
`mora biti prazno`.

## Pravila

Podprta pravila so enaka kot pri validaciji podatkov.

| `TARGET_FIELD_RULE` | Pomen |
|---|---|
| `dovoljene vrednosti` | `TARGET_FIELD` mora biti ena od vrednosti v `TARGET_FIELD_RULE_PARAM`. |
| `regex` | `TARGET_FIELD` se mora ujemati z regularnim izrazom v `TARGET_FIELD_RULE_PARAM`. |
| `ne sme biti prazno` | `TARGET_FIELD` ne sme biti prazen. |
| `mora biti prazno` | `TARGET_FIELD` mora biti prazen. |

Pri pravilih `ne sme biti prazno` in `mora biti prazno` lahko
`TARGET_FIELD_RULE_PARAM` vsebuje dodatne vrednosti, ki se štejejo kot prazne.
Vrednosti so ločene z `|`.

`TARGET_FIELD_RULE_PARAM` pri pravilu `dovoljene vrednosti` podpira enake
posebne oznake kot pri validaciji podatkov (`crke`, `crke_i`, `brez_stevilk`,
`prvi_znak_ni_stevilka`, `stevilke`, `********`, `regex(...)`, `zN-`).
Glejte `VALIDACIJA_PODATKOV.md`.

Primer:

```csv
negovan,ne sme biti prazno,Ni vrednosti,rfaza,1|2|3
zasnova,mora biti prazno,Ni vrednosti,rfaza,3|4|5
```

Pri prvem pravilu sta prazna vrednost in `Ni vrednosti` neveljavni. Pri drugem
pravilu so prazna vrednost in `Ni vrednosti` veljavne, druge vrednosti pa ne.

## Pogojne vrednosti

`CONDITION_FIELD_VALUE` lahko vsebuje eno vrednost ali več vrednosti, ločenih z
`|`.

```csv
zasnova,ne sme biti prazno,,rfaza,1|2|10
```

Pravilo se izvede, kadar je `rfaza` enaka `1`, `2` ali `10`.

Znak `¬` na začetku vrednosti pomeni negacijo.

```csv
zasnova,ne sme biti prazno,,rfaza,¬1|¬2
```

Pravilo se izvede, kadar `rfaza` ni `1` in ni `2`. Pri negiranih pogojih se pravilo
izvede tudi za prazno vrednost pogoja.

`|` je rezerviran kot ločilo med vrednostmi. Vrednosti, ki vsebujejo vejico, morajo
biti zapisane v narekovajih, npr. `"RAZNOMERNO (PS-ŠP, PREB)"`.

## Velike in male črke

Primerjava vrednosti je dobesedna (case-sensitive). `PANJEVEC` ni enako `panjevec`, `Ni vrednosti`
ni enako `NI VREDNOSTI`.

Imena atributov v CSV morajo biti zapisana enako kot v sloju.

## Določanje veljavnosti

Če pogoj ni izpolnjen, se vrstica ne upošteva. `TARGET_FIELD` je v tem primeru
neomejen, razen če zanj velja drugo pravilo.

Če je za isti objekt izpolnjenih več pravil za isti `TARGET_FIELD`, morajo veljati
vsa ta pravila. To lahko povzroči več napak za isti atribut, kadar sta zapisana dva
enakovredna sklopa pravil, npr. en sklop za `rfaza` in drug sklop za `rfaza_naziv`.

## Primer ZGS

Primer uporablja dva aktivna sklopa pravil. Prvi sklop uporablja šifro razvojne faze
(`rfaza`), drugi sklop uporablja naziv razvojne faze (`rfaza_naziv`).

```csv
TARGET_FIELD,TARGET_FIELD_RULE,TARGET_FIELD_RULE_PARAM,CONDITION_FIELD,CONDITION_FIELD_VALUE
; ----- rfaza -----
; bele celice: polje ne sme biti prazno
zasnova,ne sme biti prazno,,rfaza,1|2|10
negovan,ne sme biti prazno,,rfaza,1|2|3|4|5|6|7
sklep,ne sme biti prazno,,rfaza,1|2|3
; sive celice: polje mora biti prazno
zasnova,mora biti prazno,Ni vrednosti,rfaza,3|4|5|6|7|8|9
negovan,mora biti prazno,Ni vrednosti,rfaza,8|9|10
sklep,mora biti prazno,Ni vrednosti,rfaza,4|5|6|7|8|9|10

; ----- rfaza_naziv -----
; bele celice: polje ne sme biti prazno
zasnova,ne sme biti prazno,Ni vrednosti,rfaza_naziv,MLADOVJE|DROGOVNJAK|PIONIRSKI GOZD Z GRMIŠČI
negovan,ne sme biti prazno,Ni vrednosti,rfaza_naziv,"MLADOVJE|DROGOVNJAK|DEBELJAK|SESTOJ V OBNOVI|DVOSLOJNI SESTOJ|RAZNOMERNO (PS-ŠP, PREB)|RAZNOMERNO (SK-GNZ)"
sklep,ne sme biti prazno,Ni vrednosti,rfaza_naziv,MLADOVJE|DROGOVNJAK|DEBELJAK
; sive celice: polje mora biti prazno
zasnova,mora biti prazno,Ni vrednosti,rfaza_naziv,"DEBELJAK|SESTOJ V OBNOVI|DVOSLOJNI SESTOJ|RAZNOMERNO (PS-ŠP, PREB)|RAZNOMERNO (SK-GNZ)|PANJEVEC|GRMIČAV GOZD"
negovan,mora biti prazno,Ni vrednosti,rfaza_naziv,PANJEVEC|GRMIČAV GOZD|PIONIRSKI GOZD Z GRMIŠČI
sklep,mora biti prazno,Ni vrednosti,rfaza_naziv,"SESTOJ V OBNOVI|DVOSLOJNI SESTOJ|RAZNOMERNO (PS-ŠP, PREB)|RAZNOMERNO (SK-GNZ)|PANJEVEC|GRMIČAV GOZD|PIONIRSKI GOZD Z GRMIŠČI"
```

## Primer EHVZ

```csv
TARGET_FIELD,TARGET_FIELD_RULE,TARGET_FIELD_RULE_PARAM,CONDITION_FIELD,CONDITION_FIELD_VALUE
IZVOR,dovoljene vrednosti,1,VRSTA,1|3|4
IZVOR,dovoljene vrednosti,2,VRSTA,2
STALNOST,dovoljene vrednosti,3|4,VRSTA,1|2|3|4
STANJE,dovoljene vrednosti,9999,VRSTA,1|3|4
STANJE,dovoljene vrednosti,2,VRSTA,2
TIP_TV,dovoljene vrednosti,1,VRSTA,1|3|4
TIP_TV,dovoljene vrednosti,2|3|4|5|6,VRSTA,2
```
