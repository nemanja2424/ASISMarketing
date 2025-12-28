# KAMPANJE FEATURE

## Opis
Kampanje omogućavaju pokretanje više profila u jednom klipu. Svaka kampanja može sadržavati:
- Listu odabranih profila
- Listu odabranih kategorija profila
- Metadata (naziv, datum kreiranja)

## Struktura Podataka
Kampanje se čuvaju kao JSON fajlovi u `campaigns/` folderu:

```json
{
  "name": "Naziv Kampanje",
  "profiles": ["profile_id_1", "profile_id_2"],
  "categories": ["Marketing", "Testing"],
  "created_at": "2025-01-15T10:00:00+00:00"
}
```

## GUI Funkcionalnosti

### Kampanje Stranica
- Lista svih dostupnih kampanja sa brojem odabranih profila
- Dugmići za svaku kampanju:
  - **Odaberi Profila**: Otvara dijalog za selekciju profila po kategoriji
  - **Run**: Pokreće sve profila iz kampanje sekvencijalno
  - **Obriši**: Briše kampanju

- **+ Nova Kampanja**: Kreira novu praznu kampanju

### Dijalog za Selekciju Profila
- Profili su grupirani po kategoriji
- Checkbox za celu kategoriju (★ KATEGORIJA (SVE)) - selektuje sve profile u kategoriji
- Checkboxi za pojedine profile
- Automatski update kategorije checkbox-a kada se menja status profila
- Sačuvaj dugme čuva odabir u kampanju JSON file

## Korišćenje

### Pravljenje kampanje
1. Kliknite "Kampanje" u bokovnoj traci
2. Kliknite "+ Nova Kampanja"
3. Unesite naziv kampanje
4. Kliknite "Kreiraj"

### Dodavanje profila u kampanju
1. Izaberite kampanju iz liste
2. Kliknite "Odaberi Profila"
3. Selektujte željene profile:
   - Kliknite checkbox pored profila da ga izaberete
   - Ili kliknite "★ KATEGORIJA (SVE)" da izaberete sve profile iz te kategorije
4. Kliknite "Sačuraj"

### Pokretanje kampanje
1. Izaberite kampanju iz liste
2. Kliknite "Run"
3. Potrdite da ste sigurni
4. Svi profila će biti pokrenut sekvencijalno sa proxy podesavanjima

### Brisanje kampanje
1. Izaberite kampanju iz liste
2. Kliknite "Obriši"
3. Potrdite brisanje

## Tehnički Detalji

### Integracija sa Run Procesima
Svaki profil u kampanju se pokreće sa:
- Proxy template iz `profiles/config.json`
- Prvi dostupni namespace profila
- Multiprocessing Process za neblokiranje UI-ja

### Sigurnost
- Kategorije za profila učitavaju iz profile metadata
- Kampanja JSON je obična tekstualna datoteka lako editable
- Nema special validation - za sada radi sa svim profil ID-eva

## Budućnosti Proširenja
- [ ] Batch operacije (obrisati više kampanja)
- [ ] Schedule-ovanje pokretanja kampanja
- [ ] Log pokretanja svakog profila iz kampanje
- [ ] Export/import kampanja
- [ ] Dupiranje kampanja
- [ ] Sortiranje kampanja po datumu kreiranja
