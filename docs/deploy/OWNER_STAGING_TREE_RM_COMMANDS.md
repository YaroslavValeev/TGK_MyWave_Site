# Owner — remove unused staging tree (~1.9G)

**Status 2026-07-31:** **CLOSED PASS**  
- `/var/www/mywave-staging` removed  
- `mywave-staging.service` removed · daemon-reload  
- `sites-available/staging.mywavewake.ru` removed · nginx -t + reload ok  
- disk `/` **61% / 20G free** · site+parser active · health ok  

Pref diagnose: inactive/disabled · :5002 closed · nginx clean · DNS NXDOMAIN · only docs + dead unit refs.
