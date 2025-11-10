import sqlite3
import pandas as pd

conn = sqlite3.connect('bbm_stm_v1.db')

#Drop table 
conn.execute("""DROP TABLE foc_targets""")

#Create the agent Table 
conn.execute("""CREATE TABLE foc_targets
         (requestSource  TEXT,
         product TEXT,
         serviceRegion TEXT,
         requestType TEXT,
         focTarget INT)
        """ )

df = pd.read_csv("foc_targets.csv")

df.to_sql('foc_targets', conn, if_exists = 'append', index = False)

# We need to commit this connection to the database
conn.commit()


#print ("Table created successfully")
# Close our connection
# anytime we need to close the connection for best practice
conn.close()