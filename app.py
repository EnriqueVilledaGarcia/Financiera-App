import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
import io
from base64 import b64encode
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from functools import wraps

#Cargar las variables de entorno

load_dotenv()


#Crar instancia

app = Flask(__name__)


#Configuracion de DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuración de la clave secreta para la sesión
app.secret_key = 'clave_secreta_segura'

# Inyecta datetime en el contexto de las plantillas
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# Decorador para verificar si el usuario ha iniciado sesión
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))  # Redirigir al login si no hay sesión activa
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def verificar_sesion():
    rutas_sin_proteccion = [
        'login', 'register', 'static', 'logout', 'root'
    ]  # Rutas que no requieren autenticación
    ruta_actual = request.endpoint  # Obtener el nombre de la ruta actual

    # Verificar si la ruta actual no está en las rutas sin protección
    if ruta_actual not in rutas_sin_proteccion and 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir al login si no hay sesión activa

#Modelo de la base de datos

#clientes
class Cliente(db.Model):
    __tablename__ = 'clientes'
    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String)
    ap_paterno = db.Column(db.String)
    ap_materno = db.Column(db.String)
    telefono = db.Column(db.String)

    def to_dict(self):
        return{
            'id_cliente': self.id_cliente,
            'nombre': self.nombre,
            'ap_paterno': self.ap_paterno,
            'ap_materno': self.ap_materno,
            'telefono': self.telefono,
        }
    
#creditos

class Creditos(db.Model):
    __tablename__ = 'creditos'
    id_credito = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    monto = db.Column(db.String)
    interes = db.Column(db.String)
    total = db.Column(db.String)
    total_original = db.Column(db.String)  # Nueva columna para almacenar el valor original del crédito
    no_pagos = db.Column(db.String)
    fecha_inicio = db.Column(db.String)
    fecha_fin = db.Column(db.String)

    # Relación con Cliente
    cliente = db.relationship('Cliente', backref=db.backref('creditos', lazy=True))

    def to_dict(self):
        return {
            'id_credito': self.id_credito,
            'id_cliente': self.id_cliente,
            'monto': self.monto,
            'interes': self.interes,
            'total': self.total,
            'total_original': self.total_original,  # Incluir total_original en el diccionario
            'no_pagos': self.no_pagos,
            'fecha_inicio': self.fecha_inicio,
            'fecha_fin': self.fecha_fin
        }

#pagos
class Pagos(db.Model):
    __tablename__ = 'pagos'
    id_pago = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    id_credito = db.Column(db.Integer, db.ForeignKey('creditos.id_credito'), nullable=False)
    cantidad = db.Column(db.String)
    fecha = db.Column(db.String)
    status = db.Column(db.String)

    # Relación con Cliente
    cliente = db.relationship('Cliente', backref=db.backref('pagos', lazy=True))

    # Relación con Crédito
    credito = db.relationship('Creditos', backref=db.backref('pagos', lazy=True))

    def to_dict(self):
        return {
            'id_pago': self.id_pago,
            'id_cliente': self.id_cliente,
            'id_credito': self.id_credito,
            'cantidad': self.cantidad,
            'fecha': self.fecha,
            'status': self.status
        }

# Modelo para la tabla financiera_datos
class FinancieraDatos(db.Model):
    __tablename__ = 'financiera_datos'
    id = db.Column(db.Integer, primary_key=True)
    monto_caja = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    monto_socios = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)

# Modelo para la tabla usuarios
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario = db.Column(db.String, nullable=False, unique=True)
    contrasena = db.Column(db.String, nullable=False)
# Crear las tablas si no existen
with app.app_context():
    db.create_all()
    db.session.commit()

# Ruta raiz
@app.route('/')
def root():
    return redirect(url_for('login'))  # Redirigir al login al iniciar la aplicación

# Ruta del menú principal
@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

@app.route('/clientes')
@login_required
def index():
    #Realiza una consulta de todos los alumnos
    clientes = Cliente.query.all()
    total_clientes = Cliente.query.count()

    return render_template('index.html', clientes=clientes, total_clientes=total_clientes)



#Ruta secundaria para crear un nuevo cliente

@app.route('/clientes/new', methods= ['GET', 'POST'])
@login_required
def create_clientes():
    try:
        if request.method=='POST':
             #Aqui se va a retornar algo.
            nombre = request.form['nombre']
            ap_paterno = request.form['ap_paterno']
            ap_materno = request.form['ap_materno']
            telefono = request.form['telefono']

        
       
            nvo_cliente = Cliente(nombre= nombre, ap_paterno=ap_paterno, ap_materno=ap_materno, telefono=telefono)

            db.session.add(nvo_cliente)
            db.session.commit()

            return redirect(url_for('index'))
        return render_template('create_cliente.html')
    except:
        return(redirect(url_for('index')))

#Eliminar un cliente

@app.route('/clientes/delete/<string:id_cliente>')
@login_required
def delete_cliente(id_cliente): 
    cliente = Cliente.query.get(id_cliente)
    if cliente:
        db.session.delete(cliente)
        db.session.commit()
    return redirect(url_for('index'))

#Editar un cliente

@app.route('/clientes/update/<string:id_cliente>' , methods= ['GET', 'POST'])
@login_required
def update_cliente(id_cliente): 
    cliente = Cliente.query.get(id_cliente)
    if request.method == 'POST':
        cliente.nombre = request.form['nombre']
        cliente.ap_paterno = request.form['ap_paterno']
        cliente.ap_materno = request.form['ap_materno']
        cliente.telefono = request.form['telefono']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('update.html', cliente=cliente)


#Visualizar todos los creditos 

@app.route('/creditos')
@login_required
def creditos():
    #Realiza una consulta de todos los creditos
    creditos = Creditos.query.all()
    clientes = Cliente.query.all()
    current_date = datetime.now().date()

    # Convertir fecha_fin y fecha_inicio a objetos datetime.date si son string
    for credito in creditos:
        if isinstance(credito.fecha_fin, str):
            try:
                credito.fecha_fin = datetime.strptime(credito.fecha_fin, '%Y-%m-%d').date()
            except ValueError:
                try:
                    credito.fecha_fin = datetime.strptime(credito.fecha_fin, '%d/%m/%Y').date()
                except ValueError:
                    pass  # Dejar como string si no se puede convertir
        if isinstance(credito.fecha_inicio, str):
            try:
                credito.fecha_inicio = datetime.strptime(credito.fecha_inicio, '%Y-%m-%d').date()
            except ValueError:
                try:
                    credito.fecha_inicio = datetime.strptime(credito.fecha_inicio, '%d/%m/%Y').date()
                except ValueError:
                    pass
        # Convertir total y total_original a float si son string
        if isinstance(credito.total, str):
            try:
                credito.total = float(credito.total)
            except ValueError:
                credito.total = 0.0
        if isinstance(credito.total_original, str):
            try:
                credito.total_original = float(credito.total_original)
            except ValueError:
                credito.total_original = 0.0

    # Calcular estadísticas
    total_creditos = len(creditos)
    creditos_vigentes = 0
    creditos_vencidos = 0
    
    for credito in creditos:
        if credito.total == 0:
            # Crédito pagado - no cuenta como vigente ni vencido
            continue
        elif credito.fecha_fin < current_date:
            # Crédito vencido
            creditos_vencidos += 1
        else:
            # Crédito vigente
            creditos_vigentes += 1

    return render_template('creditos.html', 
                         creditos=creditos, 
                         clientes=clientes, 
                         current_date=current_date,
                         total_creditos=total_creditos,
                         creditos_vigentes=creditos_vigentes,
                         creditos_vencidos=creditos_vencidos)

# Ruta para generar PDF automáticamente de créditos
@app.route('/creditos/pdf')
@login_required
def creditos_pdf():
    try:
        # Realiza una consulta de todos los creditos (misma lógica que creditos())
        creditos = Creditos.query.all()
        current_date = datetime.now().date()

        # Convertir fecha_fin y fecha_inicio a objetos datetime.date si son string (misma lógica)
        for credito in creditos:
            if isinstance(credito.fecha_fin, str):
                try:
                    credito.fecha_fin = datetime.strptime(credito.fecha_fin, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        credito.fecha_fin = datetime.strptime(credito.fecha_fin, '%d/%m/%Y').date()
                    except ValueError:
                        pass
            if isinstance(credito.fecha_inicio, str):
                try:
                    credito.fecha_inicio = datetime.strptime(credito.fecha_inicio, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        credito.fecha_inicio = datetime.strptime(credito.fecha_inicio, '%d/%m/%Y').date()
                    except ValueError:
                        pass
            # Convertir total y total_original a float si son string
            if isinstance(credito.total, str):
                try:
                    credito.total = float(credito.total)
                except ValueError:
                    credito.total = 0.0
            if isinstance(credito.total_original, str):
                try:
                    credito.total_original = float(credito.total_original)
                except ValueError:
                    credito.total_original = 0.0

        # Crear buffer en memoria para el PDF
        buffer = io.BytesIO()
        
        # Crear el documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        # Obtener estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], alignment=TA_CENTER, spaceAfter=20)
        
        # Elementos para el PDF
        elements = []
        
        # Agregar logotipo
        try:
            logo_path = os.path.join(app.static_folder, 'logotipo.png')
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=2*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 12))
        except:
            pass
        
        # Título
        title = Paragraph("Reporte de Créditos", title_style)
        elements.append(title)
        
        # Fecha de generación
        fecha_generacion = Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                                   ParagraphStyle('DateStyle', parent=styles['Normal'], alignment=TA_CENTER, spaceAfter=20))
        elements.append(fecha_generacion)
        
        # Crear datos para la tabla
        data = [['Estatus', 'Cliente', 'F. Inicio', 'F. Fin', 'Total Original', 'Restante']]
        
        # Ordenar créditos por estatus
        creditos_sorted = sorted(creditos, key=lambda c: (
            0 if (isinstance(c.fecha_fin, date) and c.fecha_fin < current_date and c.total > 0) else  # Vencidos
            1 if (isinstance(c.fecha_fin, date) and c.total > 0 and (c.fecha_fin - current_date).days <= 20) else  # Próximos a vencer
            2  # Otros
        ))
        
        for credito in creditos_sorted:
            # Determinar estatus
            if credito.total == 0:
                estatus = "Pagado"
            elif isinstance(credito.fecha_fin, date) and credito.fecha_fin < current_date:
                dias_vencido = (current_date - credito.fecha_fin).days
                estatus = f"Vencido ({dias_vencido}d)"
            elif isinstance(credito.fecha_fin, date) and (credito.fecha_fin - current_date).days <= 20 and credito.total > 0:
                dias_restantes = (credito.fecha_fin - current_date).days
                estatus = f"Próximo ({dias_restantes}d)"
            else:
                estatus = "Vigente"
            
            # Nombre completo del cliente
            nombre_cliente = f"{credito.cliente.nombre} {credito.cliente.ap_paterno} {credito.cliente.ap_materno}"
            
            # Formatear fechas
            fecha_inicio = credito.fecha_inicio.strftime('%d/%m/%Y') if isinstance(credito.fecha_inicio, date) else str(credito.fecha_inicio)
            fecha_fin = credito.fecha_fin.strftime('%d/%m/%Y') if isinstance(credito.fecha_fin, date) else str(credito.fecha_fin)
            
            # Formatear montos
            total_original = f"${credito.total_original:,.2f}"
            restante = f"${credito.total:,.2f}"
            
            data.append([estatus, nombre_cliente, fecha_inicio, fecha_fin, total_original, restante])
        
        # Crear tabla
        table = Table(data, colWidths=[1.2*inch, 2*inch, 0.9*inch, 0.9*inch, 1.2*inch, 1.2*inch])
        
        # Estilo de la tabla
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Contenido
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternar colores de fila
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        
        # Generar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Crear respuesta HTTP
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=creditos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        buffer.close()
        return response
        
    except Exception as e:
        flash(f'Error al generar el PDF: {str(e)}', 'danger')
        return redirect(url_for('creditos'))

@app.route('/creditos/new', methods=['GET', 'POST'])
@login_required
def create_creditos():
    clientes = Cliente.query.all()  # Obtener todos los clientes para el formulario
    try:
        if request.method == 'POST':
            # Obtener los datos del formulario
            id_cliente = request.form['id_cliente']
            monto = float(request.form['monto'])  # Convertir monto a número
            interes_porcentaje = float(request.form['interes'])  # Convertir interés a número
            interes = monto * (interes_porcentaje / 100)  # Calcular el monto del interés
            total = monto + interes  # Calcular el total
            no_pagos = int(request.form['no_pagos'])  # Convertir número de pagos a entero
            fecha_inicio = request.form['fecha_inicio']
            fecha_fin = request.form['fecha_fin']

            # Crear un nuevo crédito
            nuevo_credito = Creditos(
                id_cliente=id_cliente,
                monto=monto,
                interes=interes_porcentaje,  # Guardar el porcentaje de interés
                total=total,
                total_original=total,  # Guardar el valor original del crédito
                no_pagos=no_pagos,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )

            # Guardar el nuevo crédito en la base de datos
            db.session.add(nuevo_credito)
            db.session.commit()

            # Redirigir a la página principal
            return redirect(url_for('creditos'))

        # Renderizar el formulario si el método es GET
        return render_template('create_credito.html', clientes=clientes)

    except Exception as e:
        # En caso de error, imprimir el error y redirigir al menú
        print(f"Error: {e}")
        return redirect(url_for('menu'))
    

@app.route('/detalle_credito/<int:id_cliente>/<int:id_credito>')
@login_required
def detalle_credito(id_cliente, id_credito):
    # Obtener el crédito específico
    creditos = Creditos.query.filter_by(id_credito=id_credito).all()
    cliente = Cliente.query.filter_by(id_cliente=id_cliente).first()  # Solo un cliente
    current_date = date.today()  # Obtiene la fecha actual

    # Generar las fechas de pago para cada crédito
    for credito in creditos:
        fecha_pagos = []
        # Verificar si fecha_inicio es un string o un objeto datetime.date
        if isinstance(credito.fecha_inicio, str):
            fecha_actual = datetime.strptime(credito.fecha_inicio, '%Y-%m-%d').date() + timedelta(days=7)
        else:
            fecha_actual = credito.fecha_inicio + timedelta(days=7)  # Si ya es un objeto datetime.date

        for _ in range(int(credito.no_pagos)):
            fecha_pagos.append(fecha_actual.strftime('%Y-%m-%d'))  # Convertir a string para el template
            fecha_actual += timedelta(days=7)  # Incrementar una semana

        credito.fechas_pagos = fecha_pagos  # Agregar fechas de pago al objeto

        # Obtener los pagos registrados en la base de datos
        pagos = Pagos.query.filter_by(id_credito=credito.id_credito).all()
        for pago in pagos:
            # Asegurarse de que las fechas de los pagos estén en el formato '%Y-%m-%d'
            pago.fecha = pago.fecha.strftime('%Y-%m-%d') if isinstance(pago.fecha, datetime) else pago.fecha
        credito.pagos = pagos

    return render_template('fechas_pagos.html', creditos=creditos, cliente=cliente, current_date=current_date)

@app.route('/credito/delete/<int:id_credito>')
@login_required
def delete_credito(id_credito):
    try:
        # Obtener el crédito
        credito = Creditos.query.get(id_credito)
        if credito:
            # Eliminar los pagos asociados
            Pagos.query.filter_by(id_credito=id_credito).delete()

            # Eliminar el crédito
            db.session.delete(credito)
            db.session.commit()
        return redirect(url_for('creditos'))
    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('creditos'))


@app.route('/marcar_pago/<int:id_credito>/<fecha>', methods=['POST'])
@login_required
def marcar_pago(id_credito, fecha):
    try:
        # Obtener los datos del formulario
        cantidad = float(request.form['cantidad'])
        credito = Creditos.query.filter_by(id_credito=id_credito).first()
        id_cliente = credito.id_cliente

        # Insertar el pago en la tabla Pagos
        nuevo_pago = Pagos(
            id_cliente=id_cliente,
            id_credito=id_credito,
            cantidad=cantidad,
            fecha=fecha,
            status='Pagado'
        )
        db.session.add(nuevo_pago)

        # Restar la cantidad al total del crédito
        credito.total = float(credito.total) - cantidad
        if credito.total < 0:
            credito.total = 0  # Evitar valores negativos

        # Guardar los cambios en la base de datos
        db.session.commit()

        return redirect(url_for('detalle_credito', id_cliente=id_cliente, id_credito=id_credito))
    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('menu'))
    
@app.route('/cancelar_pago/<int:id_credito>/<fecha>', methods=['POST'])
@login_required
def cancelar_pago(id_credito, fecha):
    try:
        # Obtener el crédito
        credito = Creditos.query.filter_by(id_credito=id_credito).first()
        if not credito:
            flash("Crédito no encontrado", "danger")
            return redirect(url_for('detalle_credito', id_cliente=credito.id_cliente, id_credito=id_credito))

        # Buscar el pago realizado en la fecha especificada
        pago_realizado = Pagos.query.filter_by(id_credito=id_credito, fecha=fecha).first()
        if not pago_realizado:
            flash("Pago no encontrado", "danger")
            return redirect(url_for('detalle_credito', id_cliente=credito.id_cliente, id_credito=id_credito))

        # Revertir el pago
        credito.total = float(credito.total) + float(pago_realizado.cantidad)
        db.session.delete(pago_realizado)
        db.session.commit()

        flash("Pago cancelado exitosamente", "success")
        return redirect(url_for('detalle_credito', id_cliente=credito.id_cliente, id_credito=id_credito))
    except Exception as e:
        print(f"Error: {e}")
        flash("Error al cancelar el pago", "danger")
        return redirect(url_for('menu'))

@app.route('/total', methods=['GET', 'POST'])
@login_required
def total():
    try:
        # Obtener todos los créditos y sumar sus totales
        creditos = Creditos.query.all()
        monto_total = 0.0
        
        for credito in creditos:
            try:
                valor_a_convertir = None
                
                if credito.total is not None and credito.total != '':
                    # Convertir a string para procesamiento uniforme
                    total_str = str(credito.total).strip()
                    
                    if total_str:
                        # Limpiar el string de caracteres no numéricos comunes
                        total_limpio = total_str.replace(',', '').replace('$', '').replace(' ', '')
                        
                        # Intentar diferentes formatos
                        if total_limpio and total_limpio not in ['', '0', '0.0', '0.00', 'None', 'null']:
                            try:
                                # Manejar casos especiales como decimales con punto o coma
                                if ',' in total_limpio and '.' not in total_limpio:
                                    # Caso: formato europeo con coma como decimal (ej: "1500,50")
                                    total_limpio = total_limpio.replace(',', '.')
                                elif ',' in total_limpio and '.' in total_limpio:
                                    # Caso: formato con separadores de miles (ej: "1,500.50")
                                    partes = total_limpio.split('.')
                                    if len(partes) == 2 and len(partes[1]) <= 2:
                                        # El último punto es decimal
                                        total_limpio = partes[0].replace(',', '') + '.' + partes[1]
                                    else:
                                        # Todos son separadores de miles
                                        total_limpio = total_limpio.replace(',', '').replace('.', '')
                                
                                valor_a_convertir = float(total_limpio)
                                
                            except (ValueError, TypeError):
                                # Si falla la conversión, intentar como entero
                                try:
                                    valor_a_convertir = float(int(total_limpio.split('.')[0]))
                                except (ValueError, TypeError, IndexError):
                                    continue
                
                # Solo sumar valores válidos y mayores a 0
                if valor_a_convertir is not None and valor_a_convertir > 0:
                    monto_total += valor_a_convertir
                    
            except Exception:
                # Si hay cualquier error, continuar con el siguiente crédito
                continue

        # Recuperar los datos de la financiera con manejo de errores
        try:
            financiera_datos = FinancieraDatos.query.order_by(FinancieraDatos.id.desc()).first()
            monto_caja = 0.0
            monto_socios = 0.0
            
            if financiera_datos:
                try:
                    monto_caja = float(str(financiera_datos.monto_caja).replace(',', '').replace('$', '')) if financiera_datos.monto_caja else 0.0
                except (ValueError, TypeError):
                    monto_caja = 0.0
                    
                try:
                    monto_socios = float(str(financiera_datos.monto_socios).replace(',', '').replace('$', '')) if financiera_datos.monto_socios else 0.0
                except (ValueError, TypeError):
                    monto_socios = 0.0
            
        except Exception:
            financiera_datos = None
            monto_caja = 0.0
            monto_socios = 0.0
        
        # Calcular el total de la financiera
        total_financiera = monto_total + monto_caja + monto_socios
        
    except Exception as e:
        # Si hay cualquier error general, usar valores por defecto
        monto_total = 0.0
        monto_caja = 0.0  
        monto_socios = 0.0
        total_financiera = 0.0
        financiera_datos = None

    if request.method == 'POST':
        try:
            # Obtener y validar los valores del formulario
            monto_caja_str = request.form.get('montoCaja', '').strip()
            monto_socios_str = request.form.get('montoSocios', '').strip()
            
            monto_caja = 0.0
            monto_socios = 0.0
            
            if monto_caja_str:
                try:
                    monto_caja = float(monto_caja_str.replace(',', ''))
                except ValueError:
                    flash(f"Error: Monto de caja '{monto_caja_str}' no es un número válido", "error")
                    return redirect(url_for('total'))
            
            if monto_socios_str:
                try:
                    monto_socios = float(monto_socios_str.replace(',', ''))
                except ValueError:
                    flash(f"Error: Monto de socios '{monto_socios_str}' no es un número válido", "error")
                    return redirect(url_for('total'))

            # Actualizar o crear registro en la base de datos
            if financiera_datos:
                financiera_datos.monto_caja = monto_caja
                financiera_datos.monto_socios = monto_socios
                financiera_datos.fecha_actualizacion = datetime.utcnow()
            else:
                nueva_financiera = FinancieraDatos(
                    monto_caja=monto_caja,
                    monto_socios=monto_socios
                )
                db.session.add(nueva_financiera)

            db.session.commit()

            # Recalcular el total financiero
            total_financiera = monto_total + monto_caja + monto_socios
            
            flash("Datos actualizados correctamente", "success")
            
        except Exception as e:
            print(f"Error al guardar datos: {e}")
            flash("Error al guardar los datos", "error")
            db.session.rollback()

    # Obtener datos para gráfica de créditos por mes
    creditos_por_año_mes = {}
    años_disponibles = set()
    
    for credito in creditos:
        try:
            # Verificar si fecha_inicio es una cadena o ya es un objeto date/datetime
            if isinstance(credito.fecha_inicio, (date, datetime)):
                fecha_obj = credito.fecha_inicio
                if isinstance(fecha_obj, date) and not isinstance(fecha_obj, datetime):
                    # Si es un objeto date, crear un datetime para mantener consistencia
                    fecha_obj = datetime.combine(fecha_obj, datetime.min.time())
            elif isinstance(credito.fecha_inicio, str):
                # Intentar parsear la fecha en formato Y-m-d
                if '-' in credito.fecha_inicio:
                    fecha_obj = datetime.strptime(credito.fecha_inicio, '%Y-%m-%d')
                else:
                    # Intentar formato d/m/Y
                    fecha_obj = datetime.strptime(credito.fecha_inicio, '%d/%m/%Y')
            else:
                # Si no es ni string ni date, continuar con el siguiente crédito
                continue
            
            año = fecha_obj.year
            mes = fecha_obj.month
            mes_nombre = fecha_obj.strftime('%b')  # Ej: "Sep"
            
            años_disponibles.add(año)
            
            if año not in creditos_por_año_mes:
                creditos_por_año_mes[año] = {}
            
            if mes not in creditos_por_año_mes[año]:
                creditos_por_año_mes[año][mes] = {'nombre': mes_nombre, 'cantidad': 0}
            
            creditos_por_año_mes[año][mes]['cantidad'] += 1
            
        except (ValueError, AttributeError, TypeError):
            # Si no se puede parsear la fecha, continuar
            continue
    
    # Obtener año actual como filtro por defecto
    año_actual = datetime.now().year
    if año_actual not in años_disponibles and años_disponibles:
        año_actual = max(años_disponibles)
    
    # Preparar datos para el año seleccionado
    meses_del_año = []
    cantidades_del_año = []
    
    if año_actual in creditos_por_año_mes:
        # Crear lista completa de meses (1-12) para mostrar todos los meses
        for mes_num in range(1, 13):
            if mes_num in creditos_por_año_mes[año_actual]:
                mes_data = creditos_por_año_mes[año_actual][mes_num]
                meses_del_año.append(mes_data['nombre'])
                cantidades_del_año.append(mes_data['cantidad'])
            else:
                # Si no hay datos para ese mes, agregar 0
                mes_nombre = datetime(año_actual, mes_num, 1).strftime('%b')
                meses_del_año.append(mes_nombre)
                cantidades_del_año.append(0)

    return render_template(
        'total.html',
        monto_total=monto_total,
        monto_caja=monto_caja,
        monto_socios=monto_socios,
        total_financiera=total_financiera,
        meses=meses_del_año,
        cantidades=cantidades_del_año,
        años_disponibles=sorted(años_disponibles, reverse=True),
        año_seleccionado=año_actual,
        creditos_por_año_mes=creditos_por_año_mes
    )

# Ruta para registrar un nuevo usuario
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = generate_password_hash(request.form['contrasena'])  # Contraseña cifrada

        nuevo_usuario = Usuario(usuario=usuario, contrasena=contrasena)
        db.session.add(nuevo_usuario)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        usuario_obj = Usuario.query.filter_by(usuario=usuario).first()
        if usuario_obj and check_password_hash(usuario_obj.contrasena, contrasena):  # Verificación segura
            session['usuario'] = usuario_obj.usuario
            return redirect(url_for('menu'))  # Redirigir al menú si las credenciales son correctas
        else:
            return render_template('login.html', error="Credenciales incorrectas")  # Mostrar error en el formulario
    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.clear()  # Eliminar todos los datos de la sesión
    return redirect(url_for('login'))  # Redirigir al login después de cerrar sesión



if __name__=='__main__':
    app.run(debug=True, port=5001)