# QKontrola

## Namen

Vtičnik izvaja:
- atributno kontrolo nad izbranim vektorskim slojem na podlagi CSV pravil
- topološko kontrolo nad izbranim vektorskim slojem
- statistično vzorčenje po ISO 19157-1 (Annex E)
- poročanje rezultatov v zavihkih in izvoz rezultatov

## Vhodni podatki

- specifikacija pravil: `EHVZ_sloj_osi_PV_2.docx`
- CSV datoteki validacijskih pravil: `validacija_podatkov_*.csv` in `validacija_relacij_*.csv`

## Uporabniški potek

1. Izberi vektorski sloj.
2. Izberi CSV datoteko pravil.
3. Izberi vrste kontrole:
   - `Izvedi atributne kontrole`
   - `Izvedi topološke kontrole`
4. Po potrebi odpri `Nastavitve topoloških kontrol`.
5. Zaženi kontrolo.

Pravila delovanja:
- gumb `Zaženi kontrole` je omogočen samo, če je izbrana vsaj ena vrsta kontrole
- med izvajanjem kontrole in med izvozom napak je akcijski del vtičnika onemogočen
- omogočena sta prekinitev (`Prekini`) in preklapljanje med zavihki

## Atributna kontrola

Pravila so definirana v CSV datotekah dveh formatov:

| Format | Datoteka | Opis |
|---|---|---|
| **Validacija podatkov** (nepogojna) | `validacija_podatkov_*.csv` | Preverjanje vrednosti atributov. Format je opisan v `VALIDACIJA_PODATKOV.md`. |
| **Validacija relacij** (pogojna) | `validacija_relacij_*.csv` | Pravila med atributi, vključno s pravili `ne sme biti prazno` in `mora biti prazno`. Format je opisan v `VALIDACIJA_RELACIJ.md`. |

## Topološke kontrole

Nastavljive kontrole:
- `Must not have dangles`
- `Must not have duplicates`
- `Must not have invalid geometries`
- `Must not have multipart geometries`
- `Must not have pseudos`
- `Must not overlap`
- `Must not have gaps`

Prikaz kontrol v dialogu `Nastavitve topoloških kontrol` je odvisen od tipa izbranega sloja:
- točkovni sloj: `Must not have duplicates`, `Must not have invalid geometries`, `Must not have multipart geometries`
- linijski sloj: `Must not have dangles`, `Must not have duplicates`, `Must not have invalid geometries`, `Must not have multipart geometries`, `Must not have pseudos`
- poligonski sloj: `Must not have duplicates`, `Must not have invalid geometries`, `Must not have multipart geometries`, `Must not overlap`, `Must not have gaps`

V poročilu se izpišejo samo topološke kontrole, ki so relevantne za tip sloja.

## Statistično vzorčenje

Gumb `Statistično vzorčenje` ob izbiri sloja odpre dialog za izbiro
reprezentativnega vzorca po priporočilih ISO 19157-1 (Annex E).

### Uporabniški potek

1. Izberi vektorski sloj.
2. Klikni `Statistično vzorčenje`.
3. (Neobvezno) Označi `Stratificiran vzorec` in izberi atribut za stratifikacijo.
   Če ima izbrani atribut več kot 100 unikatnih vrednosti, se prikaže opozorilo.
4. Izberi izhodno mapo (izbira se zapomni v QSettings; naslednjič se odpre eno mapo višje).
5. Klikni `Izvedi vzorčenje`.

### Določanje velikosti vzorca

Velikost vzorca se določi iz tabele E.2 standarda ISO 19157-1 glede na število
objektov v sloju (velikost populacije), s 95 % stopnjo zaupanja:

| Velikost populacije | Velikost vzorca |
|---|---|
| 1-8 | vsi objekti |
| 9-50 | 8 |
| 51-90 | 13 |
| 91-150 | 20 |
| 151-280 | 32 |
| 281-400 | 50 |
| 401-500 | 60 |
| 501-1200 | 80 |
| 1201-3200 | 125 |
| 3201-10000 | 200 |
| 10001-35000 | 315 |
| 35001-150000 | 500 |
| 150001-500000 | 800 |
| > 500000 | 1250 |

### Načini vzorčenja

- **Enostavno naključno vzorčenje**: vsi objekti imajo enako verjetnost izbora.
- **Stratificirano naključno vzorčenje**: objekti se izbirajo znotraj vrednosti
  izbranega atributa sorazmerno z njihovo zastopanostjo v populaciji.
- **Prostorska porazdelitev**: vzorčni objekti se samodejno razporedijo preko
  mreže prostorskih celic, da se prepreči gručenje.

### Rezultat

V izbrano mapo se shranita:
- `vzorec_<sloj>_<cas>.gpkg`: sloj z izbranimi vzorčnimi objekti (doda se v projekt,
  ime sloja je `<osnovni sloj>__vzorec`)
- `porocilo_vzorcenje_<sloj>_<cas>.html`: poročilo z velikostjo populacije,
  velikostjo vzorca, deleži strata (če je stratificirano) in seznamom FID

Po končanem vzorčenju se izbirnik sloja samodejno preklopi na novi vzorčeni sloj,
v zavihku `Poročilo vzorčenja` pa se prikaže HTML poročilo. Zavihek `Poročilo vzorčenja`
omogoča izvoz poročila v PDF/CSV/HTML in odpiranje mape s poročilom (`Odpri mapo`).
Ob preklopu na nevzorčeni sloj se zavihek skrije; ob ponovni izbiri vzorčenega sloja
se spet prikaže s pripadajočim poročilom.

## Poročilo in prikaz napak

Zavihek `Poročilo kontrole` vsebuje:
- povzetek izvedbe
- statistiko atributnih kontrol
- statistiko topoloških kontrol
- statistiko objektov po številu napak

Zavihek `Atributne napake` vsebuje:
- tabelo atributnih napak
- paginacijo: `<<`, `<`, `>`, `>>`
- izbor velikosti strani (`Na stran`)
- prikaz odseka (`od-do / skupaj`)

Zavihek `Topološke napake` vsebuje:
- tabelo topoloških napak
- enako paginacijo kot atributne napake

Zavihek `Poročilo vzorčenja` (prvi zavihek, prikaže se samo ob izbiri vzorčenega sloja):
- HTML poročilo o vzorčenju
- izvoz v PDF / CSV / HTML
- gumb `Odpri mapo` za odpiranje mape s poročilom

Klik vrstice v tabeli napak:
- izbere objekt
- izvede zoom na objekt

## Izvozi

Izvoz poročila:
- `PDF`
- `CSV`
- `HTML` (odpiranje v brskalniku)

Izvoz napak:
- `Atributne napake -> GPKG ali CSV`
- `Topološke napake -> GPKG ali CSV`

## Obnašanje pri shranjevanju poti

- ob prvem zagonu se išče privzete CSV datoteke v mapi vtičnika
- pri naslednjih zagonih se uporabi zadnje izbrane CSV datoteke
- pri izvozih se ponudi zadnja uporabljena mapa za shranjevanje
