$env:PGPASSWORD = 'postgres'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -h 127.0.0.1 -d cisknavigator -c 'SELECT 1;'
