from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
import jwt
import datetime
import uuid

app = Flask(__name__)
CORS(app)

# Koneksi Database
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "push-db"
# Secret key untuk encoding JWT
app.config["SECRET_KEY"] = "FahruJawir"

mysql = MySQL(app)

# Konfigurasi folder untuk menyimpan gambar
UPLOAD_FOLDER = "assets/images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Pastikan folder upload ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# Fungsi untuk memeriksa ekstensi file yang diizinkan
def allowed_file(filename):
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


@app.route("/")
def getAll():
    try:
        nama = request.args.get("nama")
        rating = request.args.get("rating")
        # Koneksi Ke Database
        conn = mysql.connection.cursor()
        # Menjalankan query berdasarkan parameter yang ada
        query = """
            SELECT toko.*, kategori.nama AS nama_kategori 
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
        base_url = request.host_url
        # Konversi data menjadi list of dicts dengan nama kolom sebagai key
        result = [dict(zip(column_names, row)) for row in data]
        for item in result:
            # Pastikan gambar adalah string URL, bukan array
            if "gambar" in item:
                item["gambar"] = base_url + "assets/images/" + item["gambar"]
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


@app.route("/login", methods=["POST"])
def postLogin():
    try:
        requestBody = request.get_json()
        username = requestBody.get("username")
        password = requestBody.get("password")
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        data = cursor.fetchone()
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()

        if not data:
            return jsonify({"status": 404, "message": "Data not found"}), 404

        result = dict(zip(column_names, data))

        # Memeriksa password dan mengembalikan hanya level, name, dan username
        if result["password"] == password:
            token = jwt.encode(
                {
                    "username": result["username"],
                    "name": result["name"],
                    "level": result["level"],
                    "exp": datetime.datetime.now() + datetime.timedelta(hours=1),
                },
                app.config["SECRET_KEY"],
                algorithm="HS256",
            )

            return (
                jsonify({"token": token, "status": 201, "message": "Login Berhasil"}),
                201,
            )
        else:
            return jsonify({"status": 401, "message": "Password salah"}), 401
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"status": 500, "message": "Internal server error"}), 500


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Generate a unique filename using UUID
        file_ext = file.filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(file_path)
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "File uploaded successfully",
                    "filename": unique_filename,
                }
            ),
            201,
        )

    return jsonify({"status": "error", "message": "Invalid file format"}), 400


@app.route("/assets/images/<filename>")
def uploaded_file(filename):
    return send_from_directory("assets/images", filename)


@app.route("/create-toko", methods=["POST"])
def create_toko():
    data = request.get_json()

    if not all(key in data for key in ("nama", "alamat", "rating", "gambar")):
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    nama = data["nama"]
    alamat = data["alamat"]
    rating = data["rating"]
    gambar = data["gambar"]
    kategori = data["id_kategori"]

    # Validasi rating
    if not isinstance(rating, (int, float)) or rating < 0 or rating > 5:
        return jsonify({"status": "error", "message": "Invalid rating"}), 400

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO toko (nama, alamat, rating, gambar, id_kategori) VALUES (%s, %s, %s, %s, %s)",
            (nama, alamat, rating, gambar, kategori),
        )
        mysql.connection.commit()
        cursor.close()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Toko created successfully",
                    "toko": {
                        "nama": nama,
                        "alamat": alamat,
                        "rating": rating,
                        "gambar": gambar,
                    },
                }
            ),
            201,
        )
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
