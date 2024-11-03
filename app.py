from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import User, Client, UserClient, Notification, db
from config import SQLALCHEMY_DATABASE_URI

import pytz  # Biblioteca para gerenciamento de fusos horários
from datetime import datetime
import os
from sqlalchemy import create_engine

# Configuração do fuso horário para São Paulo
TZ = pytz.timezone('America/Sao_Paulo')
os.environ['TZ'] = 'America/Sao_Paulo'

# Configuração do Flask e SQLAlchemy
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

# Configuração para uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

# Configuração da engine SQLAlchemy para garantir o uso do timezone
engine = create_engine(f"{SQLALCHEMY_DATABASE_URI}?time_zone=America/Sao_Paulo")

def allowed_file(filename):
    """Verifica se o arquivo é permitido."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def before_request():
    """Inicializa o banco de dados e cria o usuário admin se não existir."""
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                admin_user = User(
                    username='admin',
                    password=generate_password_hash('admin123'),
                    is_admin=True,
                    sector='Administração',
                    created_at=datetime.now(TZ)
                )
                db.session.add(admin_user)
                db.session.commit()
                print("Usuário admin criado: admin / Senha: admin123")
        app.db_initialized = True

@app.route('/delete_client/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """Rota para excluir um cliente."""
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Cliente não encontrado"}), 404

    db.session.delete(client)
    db.session.commit()
    return jsonify({"message": "Cliente excluído com sucesso!"}), 200

@app.route('/edit_client/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = Client.query.get(client_id)
    if not client:
        flash("Cliente não encontrado.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        client.name = request.form['name']
        client.email = request.form['email']
        client.sector = request.form['sector']
        client.phone = request.form['phone']
        client.meeting_date = request.form.get('meeting_date')
        client.video_link = request.form.get('video_link')
        client.comments = request.form.get('comments')

        # Verificar se uma nova imagem foi enviada
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                client.image_url = url_for('static', filename=f'uploads/{filename}', _external=True)

        db.session.commit()
        flash(f"Cliente '{client.name}' atualizado com sucesso!")
        return redirect(url_for('dashboard'))

    return render_template('edit_client.html', client=client)

@app.route('/analytics', methods=['GET'])
def analytics():
    """Rota para exibir a análise mensal de clientes por setor."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    clients = db.session.query(
        db.func.date_format(Client.created_at, '%Y-%m').label('month'),
        Client.sector,
        db.func.count(Client.id)
    ).group_by('month', Client.sector).all()

    monthly_data = {}
    for month, sector, count in clients:
        if month not in monthly_data:
            monthly_data[month] = {"labels": [], "data": []}
        monthly_data[month]["labels"].append(sector)
        monthly_data[month]["data"].append(count)

    return render_template('analytics.html', monthly_data=monthly_data)

@app.route('/get_client/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """Busca informações completas do cliente via AJAX."""
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Cliente não encontrado"}), 404

    meeting_date = (
        client.meeting_date if isinstance(client.meeting_date, str)
        else client.meeting_date.strftime('%Y-%m-%d') if client.meeting_date
        else ""
    )

    client_data = {
        "id": client.id,
        "name": client.name,
        "email": client.email,
        "sector": client.sector,
        "phone": client.phone,
        "meeting_date": meeting_date,
        "video_link": client.video_link,
        "comments": client.comments,
        "avatar_url": client.image_url or f"https://via.placeholder.com/150?text={client.name[:1]}"
    }
    return jsonify(client_data)

@app.route('/', methods=['GET', 'POST'])
def login():
    """Rota para login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect(url_for('analytics'))
        flash('Login inválido!')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Rota do dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    users = User.query.all()
    clients = Client.query.all()
    return render_template('dashboard.html', users=users, clients=clients)

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    """Rota para criar usuários."""
    if not session.get('is_admin'):
        flash("Acesso negado. Apenas administradores podem criar usuários.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        sector = request.form['sector']
        manager_id = request.form.get('manager_id')
        is_admin = 'is_admin' in request.form

        new_user = User(
            username=username,
            password=password,
            sector=sector,
            manager_id=int(manager_id) if manager_id else None,
            is_admin=is_admin,
            created_at=datetime.now(TZ)
        )

        db.session.add(new_user)
        db.session.commit()
        flash(f"Usuário '{username}' criado com sucesso!")
        return redirect(url_for('dashboard'))

    users = User.query.all()
    return render_template('create_user.html', users=users)

@app.route('/notifications', methods=['GET'])
def notifications():
    """Rota para obter notificações."""
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    return jsonify({"notifications": [n.message for n in notifications]})

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/create_client', methods=['GET', 'POST'])
def create_client():
    """Rota para criar clientes."""
    if 'user_id' not in session:
        flash("Você precisa estar logado para criar um cliente.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        sector = request.form['sector']
        phone = request.form.get('phone', 'N/A')
        user_ids = request.form.getlist('user_ids')

        # Lidar com o upload de imagem
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                print(f"Imagem salva em: {filepath}")
                image_url = url_for('static', filename=f'uploads/{filename}', _external=True)
        # Criar um novo cliente com a URL da imagem
        new_client = Client(
            name=name,
            email=email,
            sector=sector,
            phone=phone,
            image_url=image_url,
            created_at=datetime.now(TZ)
        )
        db.session.add(new_client)
        db.session.commit()

        # Criar uma notificação
        user = User.query.get(session['user_id'])
        notification = Notification(
            message=f"Usuário {user.username} criou o cliente {name}.",
            created_at=datetime.now(TZ)
        )
        db.session.add(notification)
        db.session.commit()

        # Relacionar cliente e usuários
        for user_id in user_ids:
            user_client = UserClient(user_id=int(user_id), client_id=new_client.id)
            db.session.add(user_client)

        db.session.commit()
        flash(f"Cliente '{name}' criado com sucesso!")
        return redirect(url_for('dashboard'))

    users = User.query.all()
    return render_template('create_client.html', users=users)


@app.route('/logout')
def logout():
    """Rota para logout."""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
