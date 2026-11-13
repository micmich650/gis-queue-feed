import psycopg

conn = psycopg.connect("postgresql://queue:queue@localhost:5432/queue")
row = conn.execute("SELECT version();").fetchone()
print(row[0])
conn.close()