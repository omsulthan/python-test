from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mysqldb import MySQL

app = Flask(__name__)
CORS(app)

# Koneksi Database
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "push-db"

mysql = MySQL(app)


@app.route("/")
def getAll():
    try:
        nama = request.args.get('nama')
        rating = request.args.get('rating')
        # Koneksi Ke Database
        conn = mysql.connection.cursor()
        # Menjalankan query berdasarkan parameter yang ada
        query = """
            SELECT toko.*, kategori.nama AS kategori_nama 
            FROM toko 
            LEFT JOIN kategori ON toko.id_kategori = kategori.id
        """
        filters = []
        parameters = []

        if nama:
            filters.append("toko.nama LIKE %s")
            parameters.append("%" + nama + "%")
        if rating:
            filters.append("toko.rating = %s")
            parameters.append(rating)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        conn.execute(query, tuple(parameters))

        # Mengambil hasil query
        data = conn.fetchall()
        column_names = [desc[0] for desc in conn.description]

        # Menutup cursor dan koneksi
        conn.close()

        # Konversi data menjadi list of dicts dengan nama kolom sebagai key
        result = [dict(zip(column_names, row)) for row in data]

        # Mengembalikan data sebagai JSON
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/id=<int:id>")
def getDataById(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM toko WHERE id = %s", (id,))
        data = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()
        result = [dict(zip(column_names, row)) for row in data]
        if not result:
            return jsonify({"status": 404, "message": "Data not found"}), 404
        return jsonify(result)
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"status": 500, "message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
