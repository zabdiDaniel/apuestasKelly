from flask import Flask, render_template_string, request, jsonify, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Inicializar base de datos
def iniciar_base_datos():
    conn = sqlite3.connect('apuestas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            bankroll REAL,
            cuota REAL,
            precision REAL,
            apuesta REAL,
            ganancia_potencial REAL,
            resultado TEXT,
            nuevo_bankroll REAL
        )
    ''')
    conn.commit()
    conn.close()

# Calcular apuesta (Kelly fraccionado)
def calcular_apuesta(bankroll, cuota, prob_exito=0.91, kelly_frac=0.25, apuesta_max_frac=0.1, apuesta_min=1):
    b = cuota - 1
    p = prob_exito
    q = 1 - p
    if b <= 0:
        return 0
    f_kelly = (b * p - q) / b
    f_apuesta = f_kelly * kelly_frac
    apuesta = bankroll * f_apuesta
    apuesta = min(apuesta, bankroll * apuesta_max_frac)
    apuesta = max(apuesta, apuesta_min)
    return round(apuesta, 2)

# Página principal
@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    error = None
    if request.method == 'POST':
        try:
            bankroll = float(request.form['bankroll'])
            cuota = float(request.form['cuota'])
            prob_exito = float(request.form['precision'])
            if bankroll <= 0 or cuota <= 1 or not (0 <= prob_exito <= 1):
                error = "Valores inválidos: Bankroll > 0, Cuota > 1, Precisión entre 0 y 1."
            else:
                apuesta = calcular_apuesta(bankroll, cuota, prob_exito)
                ganancia = apuesta * (cuota - 1)
                ev = (prob_exito * ganancia) - ((1 - prob_exito) * apuesta)
                conn = sqlite3.connect('apuestas.db')
                cursor = conn.cursor()
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    INSERT INTO apuestas (fecha, bankroll, cuota, precision, apuesta, ganancia_potencial, resultado, nuevo_bankroll)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fecha, bankroll, cuota, prob_exito, apuesta, ganancia, "pendiente", bankroll))
                conn.commit()
                apuesta_id = cursor.lastrowid
                conn.close()
                resultado = {
                    'id': apuesta_id,
                    'bankroll': bankroll,
                    'cuota': cuota,
                    'precision': prob_exito,
                    'apuesta': apuesta,
                    'ganancia': ganancia,
                    'nuevo_bankroll_acierto': bankroll + ganancia,
                    'nuevo_bankroll_fallo': bankroll - apuesta,
                    'ev': ev
                }
        except ValueError:
            error = "Ingresa números válidos."
    
    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Calculadora de Apuestas</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f0f4f8; }
            .container { max-width: 600px; }
            .card { border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            .btn-primary { background-color: #0078d4; border-color: #0078d4; }
            h1 { font-family: Helvetica, Arial, sans-serif; }
        </style>
    </head>
    <body>
        <div class="container mt-4">
            <h1 class="text-center mb-4">Calculadora de Apuestas</h1>
            <div class="card p-4">
                <form method="POST">
                    <div class="mb-3">
                        <label for="bankroll" class="form-label">Bankroll ($):</label>
                        <input type="number" step="0.01" class="form-control" id="bankroll" name="bankroll" required>
                    </div>
                    <div class="mb-3">
                        <label for="cuota" class="form-label">Cuota (ej. 1.28):</label>
                        <input type="number" step="0.01" class="form-control" id="cuota" name="cuota" required>
                    </div>
                    <div class="mb-3">
                        <label for="precision" class="form-label">Precisión (0-1):</label>
                        <input type="number" step="0.01" class="form-control" id="precision" name="precision" value="0.90" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Calcular Apuesta</button>
                </form>
                {% if error %}
                    <div class="alert alert-danger mt-3">{{ error }}</div>
                {% endif %}
                {% if resultado %}
                    <div class="alert alert-success mt-3">
                        <h5>ID Apuesta: {{ resultado.id }}</h5>
                        <p>Bankroll: ${{ "%.2f" % resultado.bankroll }}</p>
                        <p>Cuota: {{ "%.2f" % resultado.cuota }}</p>
                        <p>Precisión: {{ "%.1f" % (resultado.precision * 100) }}%</p>
                        <p><strong>Apuesta: ${{ "%.2f" % resultado.apuesta }}</strong></p>
                        <p>Ganancia potencial: ${{ "%.2f" % resultado.ganancia }}</p>
                        <p>Nuevo bankroll si aciertas: ${{ "%.2f" % resultado.nuevo_bankroll_acierto }}</p>
                        <p>Nuevo bankroll si fallas: ${{ "%.2f" % resultado.nuevo_bankroll_fallo }}</p>
                        <p>Valor esperado (EV): ${{ "%.2f" % resultado.ev }}</p>
                    </div>
                {% endif %}
                <a href="/historial" class="btn btn-secondary w-100 mt-3">Ver Historial</a>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return render_template_string(html, resultado=resultado, error=error)

# Página de historial
@app.route('/historial', methods=['GET', 'POST'])
def historial():
    conn = sqlite3.connect('apuestas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apuestas")
    apuestas = cursor.fetchall()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Historial de Apuestas</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f0f4f8; }
            .container { max-width: 1000px; }
            .table { font-size: 0.9rem; }
            .btn-primary { background-color: #0078d4; border-color: #0078d4; }
            .btn-danger { background-color: #dc3545; border-color: #dc3545; }
            h1 { font-family: Helvetica, Arial, sans-serif; }
        </style>
    </head>
    <body>
        <div class="container mt-4">
            <h1 class="text-center mb-4">Historial de Apuestas</h1>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Fecha</th>
                        <th>Bankroll</th>
                        <th>Cuota</th>
                        <th>Precisión</th>
                        <th>Apuesta</th>
                        <th>Ganancia</th>
                        <th>Resultado</th>
                        <th>Nuevo Bankroll</th>
                        <th>Acción</th>
                    </tr>
                </thead>
                <tbody>
                    {% for apuesta in apuestas %}
                        <tr>
                            <td>{{ apuesta[0] }}</td>
                            <td>{{ apuesta[1] }}</td>
                            <td>${{ "%.2f" % apuesta[2] }}</td>
                            <td>{{ "%.2f" % apuesta[3] }}</td>
                            <td>{{ "%.1f" % (apuesta[4] * 100) }}%</td>
                            <td>${{ "%.2f" % apuesta[5] }}</td>
                            <td>${{ "%.2f" % apuesta[6] }}</td>
                            <td>
                                <select class="form-select resultado" data-id="{{ apuesta[0] }}">
                                    <option value="pendiente" {% if apuesta[7] == "pendiente" %}selected{% endif %}>Pendiente</option>
                                    <option value="ganada" {% if apuesta[7] == "ganada" %}selected{% endif %}>Ganada</option>
                                    <option value="perdida" {% if apuesta[7] == "perdida" %}selected{% endif %}>Perdida</option>
                                </select>
                            </td>
                            <td>${{ "%.2f" % apuesta[8] }}</td>
                            <td>
                                <a href="/eliminar_apuesta/{{ apuesta[0] }}" class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar esta apuesta?')">Eliminar</a>
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
            <a href="/" class="btn btn-primary w-100 mt-3">Volver</a>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            document.querySelectorAll('.resultado').forEach(select => {
                select.addEventListener('change', function() {
                    const id = this.dataset.id;
                    const resultado = this.value;
                    fetch('/actualizar_resultado', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: id, resultado: resultado })
                    }).then(response => response.json()).then(data => {
                        if (data.success) {
                            location.reload();
                        } else {
                            alert(data.error);
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, apuestas=apuestas)

# Actualizar resultado
@app.route('/actualizar_resultado', methods=['POST'])
def actualizar_resultado():
    data = request.get_json()
    apuesta_id = data['id']
    resultado = data['resultado']
    if resultado not in ["pendiente", "ganada", "perdida"]:
        return jsonify({'error': "Resultado inválido"}), 400
    conn = sqlite3.connect('apuestas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT bankroll, apuesta, ganancia_potencial FROM apuestas WHERE id = ?", (apuesta_id,))
    apuesta_data = cursor.fetchone()
    if not apuesta_data:
        conn.close()
        return jsonify({'error': "ID de apuesta no encontrado"}), 404
    bankroll, apuesta, ganancia = apuesta_data
    nuevo_bankroll = bankroll + ganancia if resultado == "ganada" else bankroll - apuesta if resultado == "perdida" else bankroll
    cursor.execute('''
        UPDATE apuestas SET resultado = ?, nuevo_bankroll = ?
        WHERE id = ?
    ''', (resultado, nuevo_bankroll, apuesta_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'nuevo_bankroll': nuevo_bankroll})

# Eliminar apuesta
@app.route('/eliminar_apuesta/<int:id>')
def eliminar_apuesta(id):
    conn = sqlite3.connect('apuestas.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apuestas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/historial')

if __name__ == '__main__':
    iniciar_base_datos()
    app.run(debug=True, host='0.0.0.0', port=5000)