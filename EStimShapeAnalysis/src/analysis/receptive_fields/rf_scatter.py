import numpy as np
import matplotlib.pyplot as plt
import mysql.connector

conn = mysql.connector.connect(
    host="172.30.6.61",
    user="xper_rw",
    passwd="up2nite",
    database="allen_data_repository"
)

cursor = conn.cursor()
cursor.execute("""
    SELECT session_id, radius, x, y 
    FROM ReceptiveFieldInfo 
    WHERE channel = 'SUPRA-000'
""")
rows = cursor.fetchall()
cursor.close()
conn.close()

session_ids = []
eccentricities = []
sqrt_areas = []

for session_id, radius, x, y in rows:
    if radius is not None and x is not None and y is not None:
        ecc = np.sqrt(x**2 + y**2)
        sqrt_area = np.sqrt(np.pi * radius**2)
        session_ids.append(session_id)
        eccentricities.append(ecc)
        sqrt_areas.append(sqrt_area)

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(eccentricities, sqrt_areas)

for sid, ex, sa in zip(session_ids, eccentricities, sqrt_areas):
    ax.annotate(sid, (ex, sa), fontsize=7, alpha=0.7)

ax.set_xlabel('Eccentricity (sqrt(x² + y²))')
ax.set_ylabel('sqrt(Area) (sqrt(π r²))')
ax.set_title('RF Size vs Eccentricity (SUPRA-000)')
plt.tight_layout()
# plt.savefig('/home/claude/rf_scatter.png', dpi=150)
plt.show()
print(f"Plotted {len(session_ids)} sessions")