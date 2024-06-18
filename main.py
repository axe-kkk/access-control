from flask import Flask, request, render_template, redirect, send_file, url_for, jsonify, send_from_directory, session, \
    flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from io import BytesIO
# import db_old
import datetime
import create_pass
import pyodbc
from sqlalchemy import or_, and_, func, cast, String
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload
import webview
import os

path = os.path.join(os.path.abspath(os.path.dirname(__file__)))
app = Flask(__name__, static_folder='./static', template_folder='./templates', instance_path=path + '/instance')
app.secret_key = 's3cr3t_k3y_12345'
app.config['SESSION_PERMANENT'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///AC.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    id = 1
    username = 'admin'
    password = generate_password_hash("faust0313")


# Загрузка пользователя
@login_manager.user_loader
def load_user(user_id):
    if int(user_id) == 1:
        return User()
    return None


# Маршрут для входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == User.username and check_password_hash(User.password, password):
            user = User()
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')


# Маршрут для выхода
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


class Object(db.Model):
    object_id = db.Column('ObjectId', db.Integer, primary_key=True)
    name = db.Column('Name', db.String)
    parent_obj_id = db.Column('ParentObjId', db.Integer)


class Rent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ContrId = db.Column(db.Integer, nullable=False)


class AccessLevel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pass_id = db.Column(db.Integer, nullable=False)
    access_level = db.Column(db.Integer, nullable=False)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ac_id = db.Column(db.Integer, db.ForeignKey('ac.id'), nullable=False)  # Изменено с 'a_c.id' на 'ac.id'
    filename = db.Column(db.String(100), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)


class Counterpartie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text, nullable=True)


class Pass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ac_id = db.Column(db.Integer, db.ForeignKey('ac.id'), nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)  # Дата выдачи пропуска
    valid_until = db.Column(db.DateTime, nullable=False)  # Срок действия пропуска
    car_number = db.Column(db.String(100), nullable=True)
    counterpartie = db.Column(db.String(100), nullable=False)
    access_level = db.Column(db.String(20), nullable=False)
    storages = db.Column(db.Text, nullable=True)
    ac = db.relationship('AC', backref=db.backref('passes', lazy=True))


class AC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    f_name = db.Column(db.String(255), nullable=False)
    m_name = db.Column(db.String(255), nullable=False)
    l_name = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(255), nullable=False)
    passport_id = db.Column(db.String(255), nullable=False)
    passport_date = db.Column(db.DateTime, nullable=False)
    type_doc = db.Column(db.String(255), nullable=False)
    who_write_doc = db.Column(db.String(255), nullable=True)
    filename_avatar = db.Column(db.String(255), nullable=True)
    data_avatar = db.Column(db.LargeBinary, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    documents = db.relationship('Document', backref='ac', lazy=True)


@app.route('/render')
def render():
    person = AC.query.all()
    for _ in person:
        time = person.passport_date.strftime('%Y-%m-%d')
        person.passport_date = time
    pas = Pass.query.all()
    for _ in pas:
        time1 = pas.issue_date.strftime('%Y-%m-%d')
        person.passport_date = time1


class Obj_for_pass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pass_id = db.Column(db.Integer, nullable=False)
    object_id = db.Column(db.Integer, nullable=False)


@app.route('/')
@login_required
def index():
    persons = db.session.query(AC.id, AC.f_name, AC.m_name, AC.l_name)
    return render_template('index.html', persons=persons)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:  # Проверяем, пустой ли запрос
        return redirect(url_for('index'))

    words = query.split()  # Разделяем запрос на слова
    query = AC.query
    for word in words:
        search = f"%{word}%"
        query = query.filter((AC.f_name.like(search)) | (AC.m_name.like(search)) | (AC.l_name.like(search)))
    persons = query.all()

    return render_template('index.html', persons=persons)


def read_image_data():
    with open('static/img/avatar.jpg', 'rb') as file:
        return file.read()


@app.route('/add_person', methods=['GET', 'POST'])
def add_person():
    if request.method == 'POST':
        required_fields = ['f_name', 'm_name', 'address', 'phone', 'passport_id', 'passport_date', 'type_doc']

        # Проверка, что все поля присутствуют и не пустые
        if not all(request.form.get(field, '').strip() for field in required_fields):
            return redirect(request.url)  # Перезагружаем страницу при отсутствии необходимых полей

        # Поля формы
        f_name = request.form['f_name']
        m_name = request.form['m_name']
        l_name = request.form['l_name']
        address = request.form['address']
        phone = request.form['phone']
        passport_id = request.form['passport_id']
        date = request.form['passport_date']
        passport_date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M')
        type_doc = request.form['type_doc']
        who_write_doc = request.form['who_write_doc']
        comment = request.form['comment']

        # Обработка файла
        filename_avatar = None
        data_avatar = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file.filename != '':
                filename_avatar = secure_filename(file.filename)
                data_avatar = file.read()
                print("Файл загружен:", filename_avatar)  # Логирование имени файла
                print("Размер файла:", len(data_avatar))  # Логирование размера файла
            else:
                print("Файл не был загружен")  # Логирование отсутствия файла
        else:
            filename_avatar = "avatar.jpg"
            data_avatar = read_image_data()

        # Создание новой записи
        new_person = AC(f_name=f_name, m_name=m_name, l_name=l_name, address=address, phone=phone,
                        passport_id=passport_id, passport_date=passport_date, type_doc=type_doc,
                        who_write_doc=who_write_doc, filename_avatar=filename_avatar, data_avatar=data_avatar,
                        comment=comment)
        db.session.add(new_person)
        db.session.commit()

        # Обработка документов
        files = request.files.getlist('docs_img')
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                new_document = Document(ac_id=new_person.id, filename=filename, data=file.read())
                db.session.add(new_document)
        db.session.commit()
        return redirect('/')
    return render_template('add_person.html')


def person_info(id):
    persons = db.session.query(AC.id, AC.f_name, AC.m_name, AC.l_name)
    for person in persons:
        if person.id == id:
            return person.m_name + " " + person.f_name + " " + person.l_name


def person_f_name(id):
    persons = db.session.query(AC.id, AC.f_name)
    for person in persons:
        if person.id == id:
            return person.f_name


def person_m_name(id):
    persons = db.session.query(AC.id, AC.m_name)
    for person in persons:
        if person.id == id:
            return person.m_name


def person_l_name(id):
    persons = db.session.query(AC.id, AC.l_name)
    for person in persons:
        if person.id == id:
            return person.l_name


@app.route('/person/<int:person_id>')
def person_detail(person_id):
    person = AC.query.get_or_404(person_id)
    pass_history = []
    pas = Pass.query.all()
    time = person.passport_date.strftime('%Y-%m-%d')
    for p in pas:
        if p.ac_id == person.id:
            pass_history.append(p)
    return render_template('person_detail.html', person=person, time=time, pass_history=pass_history,
                           person_info=person_info, person_f_name=person_f_name, person_m_name=person_m_name,
                           person_l_name=person_l_name)


@app.route('/document_image/<int:document_id>')
def document_image(document_id):
    document = Document.query.get_or_404(document_id)
    if not document.data:
        return 'No image', 404
    return send_file(BytesIO(document.data), mimetype='image/jpeg, image/png', as_attachment=True,
                     download_name=document.filename)


@app.route('/image/<int:person_id>')
def image(person_id):
    person = AC.query.get_or_404(person_id)
    if person.data_avatar:
        return send_file(BytesIO(person.data_avatar), mimetype='image/jpeg, image/png')
    else:
        filename = 'static/img/avatar.jpg'
        return send_file(filename, mimetype='image/jpeg')


@app.route('/update_person_docs/<int:person_id>', methods=['GET', 'POST'])
def update_person_docs(person_id):
    person = AC.query.get_or_404(person_id)
    if request.method == 'POST':
        new_files = request.files.getlist('new_docs_img')
        for f in new_files:
            if f and f.filename:
                filename = secure_filename(f.filename)
                new_document = Document(ac_id=person.id, filename=filename, data=f.read())
                db.session.add(new_document)

        db.session.commit()
        return redirect(url_for('update_person', person_id=person_id))
    return render_template('update_person.html', person=person)


@app.route('/update_person/<int:person_id>', methods=['GET', 'POST'])
def update_person(person_id):
    # Получаем информацию о человеке из базы данных
    person = AC.query.get_or_404(person_id)

    if request.method == 'POST':
        # Обновление основной информации о человеке
        person.f_name = request.form['f_name']
        person.m_name = request.form['m_name']
        person.l_name = request.form['l_name']
        person.address = request.form['address']
        person.phone = request.form['phone']
        person.passport_id = request.form['passport_id']
        passport_date_string = request.form['passport_date']
        person.passport_date = datetime.datetime.strptime(passport_date_string, '%Y-%m-%dT%H:%M')
        person.type_doc = request.form['type_doc']
        person.who_write_doc = request.form['who_write_doc']
        person.comment = request.form['comment']

        # Обновление аватара (если он был отправлен)
        avatar_file = request.files['avatar']
        if avatar_file and avatar_file.filename:
            person.filename_avatar = secure_filename(avatar_file.filename)
            person.data_avatar = avatar_file.read()

        db.session.commit()
        return redirect(url_for('update_person', person_id=person_id))

    return render_template('update_person.html', person=person)


@app.route('/delete_document/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    db.session.delete(document)
    db.session.commit()
    return redirect(url_for('update_person', person_id=document.ac_id))


@app.route('/delete_person/<int:person_id>', methods=['GET'])
def delete_person(person_id):
    person = AC.query.get_or_404(person_id)
    for document in person.documents:
        db.session.delete(document)
    db.session.delete(person)
    db.session.commit()
    return redirect('/')


@app.route('/all_pass')
def all_pass():
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Количество пропусков на странице, можно настроить по вашему усмотрению
    pas_pagination = Pass.query.options(joinedload(Pass.ac)).order_by(Pass.id.desc()).paginate(page=page,
                                                                                               per_page=per_page,
                                                                                               error_out=False)
    return render_template('all_pass.html', pas_pagination=pas_pagination, person_info=person_info,
                           person_f_name=person_f_name, person_m_name=person_m_name, person_l_name=person_l_name)


# -----------------------------------------------------------------------------------------------------------------------


@app.route('/add_pass/<int:person_id>', methods=['GET', 'POST'])
def add_pass(person_id):
    person = AC.query.get_or_404(person_id)
    cp = Counterpartie.query.all()
    nodes = Object.query.order_by(Object.parent_obj_id, Object.object_id).all()
    tree = build_tree(nodes)

    if request.method == 'POST':
        required_fields = ['issue_date', 'valid_until', 'counterpartie']

        # Проверка, что все поля присутствуют и не пустые
        if not all(request.form.get(field, '').strip() for field in required_fields):
            return redirect(request.url)

            # Получаем данные из формы
        ac_id = person_id  # ID пользователя
        issue_date = request.form['issue_date']  # Дата выдачи пропуска
        date1 = datetime.datetime.strptime(issue_date, '%Y-%m-%dT%H:%M')
        valid_until = request.form['valid_until']  # Срок действия пропуска
        date2 = datetime.datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
        car_number = request.form['car_number']
        counterpartie = request.form['counterpartie']
        selected_access_levels = request.form.getlist('access_level[]')
        access_levels_str = ','.join(selected_access_levels)

        # Создаем новый пропуск
        new_pass = Pass(ac_id=ac_id, issue_date=date1, valid_until=date2, car_number=car_number,
                        counterpartie=counterpartie, access_level=access_levels_str)
        # Добавляем пропуск в базу данных
        db.session.add(new_pass)
        db.session.commit()
        add_note(new_pass.id)
        return redirect(url_for('all_pass'))
    return render_template('add_pass.html', person=person, cps=cp, nodes=tree)


@app.route('/path_to_save', methods=['POST'])
def save_selected():
    selected_nodes = request.form.get('selectedNodes')
    session['selected_nodes'] = selected_nodes.split(',')
    arr = session.get('selected_nodes')

    return 'Сохранено успешно', 200


def build_tree(nodes, parent_obj_id=0):
    tree = []
    # Сортировка списка объектов по атрибуту name перед итерацией
    for obj in sorted(nodes, key=lambda x: x.name):
        if obj.parent_obj_id == parent_obj_id:
            children = build_tree(nodes, obj.object_id)
            tree.append({
                "object_id": obj.object_id,
                "name": obj.name,
                "children": children
            })
    return tree


# Функция для добавления узла
def add_node(object_id, name, parent_obj_id):
    new_node = Object(object_id=object_id, name=name, parent_obj_id=parent_obj_id)
    db.session.add(new_node)
    db.session.commit()


def delete_node(object_id):
    Object.query.filter_by(object_id=object_id).delete()
    db.session.commit()


def find_branch(object_id):
    # Найти узел по ID
    node = Object.query.filter_by(object_id=object_id).first()
    # Проверить, существует ли узел
    if not node:
        return "Узел не найден"
    # Строим ветку от узла к корню
    branch = node.name
    while node.parent_obj_id:
        node = Object.query.filter_by(object_id=node.parent_obj_id).first()
        if node:
            branch = node.name + '/' + branch
        else:
            break
    return branch


def add_note(pass_id):
    Obj_for_pass.query.filter_by(pass_id=pass_id).delete()

    selected_nodes = session.get('selected_nodes', [])
    for node_id in selected_nodes:
        new_note = Obj_for_pass(pass_id=pass_id, object_id=int(node_id))
        db.session.add(new_note)

    db.session.commit()

    storage = Pass.query.get_or_404(pass_id)
    paths = [find_branch(int(node_id)) for node_id in selected_nodes]
    storage.storages = "\n".join(paths)
    db.session.commit()


@app.route('/get_paths', methods=['POST'])
def get_paths():
    selected_nodes = request.form.get('selectedNodes', '').split(',')
    paths = [find_branch(int(node_id)) for node_id in selected_nodes if node_id.isdigit()]
    return '\n'.join(paths)


# ----------------------------------------------------------------------------------------------------


@app.route('/pass/<int:pass_id>')
def pass_detail(pass_id):
    pas = Pass.query.get_or_404(pass_id)
    person = AC.query.get_or_404(pas.ac_id)
    arr = pas.access_level.split(',')
    return render_template('pass_detail.html', p=pas, person=person, str=str, arr=arr)


@app.route('/download/<int:p_id>', methods=['GET'])
def download_file(p_id):
    p = Pass.query.get_or_404(p_id)
    ac = AC.query.get_or_404(p.ac_id)
    object_for_pass = Obj_for_pass.query.all()
    arr = []
    for object in object_for_pass:
        if object.pass_id == p_id:
            arr.append(object.object_id)
    storages = []
    for i in range(len(arr)):
        storages.append(pars_storage(find_branch(arr[i])))
    date1 = p.issue_date.strftime("%d/%m/%Y")
    date2 = p.valid_until.strftime("%d/%m/%Y")
    create_pass.create_pass(str(p.id), ac.f_name, ac.m_name, ac.l_name, date1, date2, p.car_number, storages)
    directory = "static/img/"  # Укажите путь к папке с изображениями
    return send_from_directory(directory, "Pass.png", as_attachment=True)


def pars_storage(text):
    storage = text.split('/')
    storages = []
    for i in storage:
        arr = i.split(' ')
        storages.append(arr)
    res = ""
    for i in storages:
        if len(i) == 3:
            res += i[0][0] + i[1][0] + i[2] + '/'
        elif len(i) == 2:
            if i[0] == 'АБК':
                res += i[0] + i[1] + '/'
            else:
                res += i[0][0] + i[1] + '/'
        else:
            res += i[0] + '/'
    return res[:len(res) - 1]


@app.route('/update_pass/<int:pass_id>', methods=['GET', 'POST'])
def update_pass(pass_id):
    # Получение записи пропуска и связанных данных
    pas = Pass.query.get_or_404(pass_id)
    person = AC.query.get_or_404(pas.ac_id)
    cp = Counterpartie.query.all()
    nodes = Object.query.order_by(Object.parent_obj_id, Object.object_id).all()
    tree = build_tree(nodes)  # Предположим, это ваша функция для построения структуры дерева

    # Получение ID выбранных объектов для данного пропуска
    selected_nodes_ids = [node.object_id for node in Obj_for_pass.query.filter_by(pass_id=pass_id).all()]

    if request.method == 'POST':
        # Обновление данных пропуска на основе данных формы
        pas.issue_date = datetime.datetime.strptime(request.form['issue_date'], '%Y-%m-%dT%H:%M')
        pas.valid_until = datetime.datetime.strptime(request.form['valid_until'], '%Y-%m-%dT%H:%M')
        pas.car_number = request.form['car_number']
        pas.counterpartie = request.form['counterpartie']
        pas.access_level = ','.join(request.form.getlist('access_level[]'))

        # Обработка выбранных объектов
        selected_nodes = [int(node_id) for node_id in request.form.get('selected_nodes', '').split(',') if
                          node_id.isdigit()]

        # Удаление текущих выбранных объектов
        Obj_for_pass.query.filter_by(pass_id=pass_id).delete()

        # Добавление новых выбранных объектов
        for node_id in selected_nodes:
            new_selection = Obj_for_pass(pass_id=pass_id, object_id=node_id)
            db.session.add(new_selection)

        db.session.commit()

        return redirect(url_for('update_pass', pass_id=pass_id))
    else:
        # Показываем форму редактирования с текущими значениями
        return render_template('update_pass.html', pas=pas, person=person, cps=cp, nodes=tree,
                               selected_nodes=selected_nodes_ids)


@app.route('/delete_pass/<int:pass_id>', methods=['GET'])
def delete_pass(pass_id):
    pass_to_delete = Pass.query.get_or_404(pass_id)
    db.session.delete(pass_to_delete)
    db.session.commit()
    return redirect('/all_pass')


'''
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:  
        return redirect(url_for('index'))

    words = query.split()
    query = AC.query
    for word in words:
        search = f"%{word}%"
        query = query.filter((AC.f_name.like(search)) | (AC.m_name.like(search)) | (AC.l_name.like(search)))
    persons = query.all()

    return render_template('index.html', persons=persons)
'''


@app.route('/search_pass')
def search_pass():
    query = request.args.get('query', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Количество результатов на странице
    if not query:  # Проверяем, пустой ли запрос
        return redirect(url_for('all_pass', page=page))

    words = query.split()
    base_query = db.session.query(Pass).join(AC, Pass.ac_id == AC.id)

    # Создаем фильтр, который изначально пуст
    filters = []
    for word in words:
        search = f"%{word}%"
        word_filters = or_(
            AC.m_name.like(search),
            AC.f_name.like(search),
            AC.l_name.like(search),
            cast(Pass.id, String).like(search),  # Преобразуем id в строку для сравнения
            Pass.car_number.like(search)
        )
        filters.append(word_filters)  # Добавляем фильтры для текущего слова

    if filters:
        base_query = base_query.filter(or_(*filters))  # Применяем все собранные фильтры

    search_results = base_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('search_pass.html', pas_pagination=search_results, query=query, person_info=person_info,
                           person_f_name=person_f_name, person_m_name=person_m_name, person_l_name=person_l_name)


@app.route('/all_cp')
def all_cp():
    cp = Counterpartie.query.all()
    return render_template('all_cp.html', cps=cp, str=str)


@app.route('/add_cp', methods=['GET', 'POST'])
def add_cp():
    if request.method == 'POST':
        name = request.form['name']
        comment = request.form['comment']
        new_cp = Counterpartie(name=name, comment=comment)
        db.session.add(new_cp)
        db.session.commit()
        return redirect(url_for('all_cp'))
    return render_template('add_cp.html')


@app.route('/update_cp/<int:cp_id>', methods=['GET', 'POST'])
def update_cp(cp_id):
    cp = Counterpartie.query.get_or_404(cp_id)
    if request.method == 'POST':
        cp.name = request.form['name']
        cp.comment = request.form['comment']
        db.session.commit()
        return redirect(url_for('cp_detail', cp_id=cp_id))
    return render_template('update_cp.html', cp=cp)


@app.route('/cp/<int:cp_id>')
def cp_detail(cp_id):
    cp = Counterpartie.query.get_or_404(cp_id)
    return render_template('cp_detail.html', cp=cp)


@app.route('/delete_cp/<int:cp_id>', methods=['GET'])
def delete_cp(cp_id):
    pass_to_delete = Counterpartie.query.get_or_404(cp_id)
    db.session.delete(pass_to_delete)
    db.session.commit()
    return redirect('/all_cp')


@app.route('/all_storage')
def all_storage():
    nodes = Object.query.order_by(Object.parent_obj_id, Object.object_id).all()
    tree = build_tree(nodes)
    return render_template('all_storage.html', nodes=tree)


@app.route('/add_child/<int:parent_id>', methods=['GET', 'POST'])
def add_child(parent_id):
    noda = Object.query.all()
    max_id = 0
    for i in noda:
        if max_id < i.object_id:
            max_id = i.object_id

    if request.method == 'POST':
        name = request.form['name']
        add_node(max_id + 1, name, parent_id)
        return redirect(url_for('all_storage'))
    return render_template('add_child.html', parent_id=parent_id)


@app.route('/storage/<int:str_id>', methods=['GET', 'POST'])
def storage_detail(str_id):
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Установите желаемое количество элементов на страницу

    obj = Object.query.get_or_404(str_id)
    obj_passes = Obj_for_pass.query.filter_by(object_id=str_id).all()
    pass_ids = [p.pass_id for p in obj_passes]

    # Здесь используем paginate вместо all() для извлечения записей
    pass_history_pagination = Pass.query.filter(Pass.id.in_(pass_ids)).paginate(page=page, per_page=per_page,
                                                                                error_out=False)

    return render_template('storage_detail.html', str_id=str_id, s=obj, pas_pagination=pass_history_pagination,
                           person_info=person_info, person_f_name=person_f_name, person_m_name=person_m_name,
                           person_l_name=person_l_name)


@app.route('/delete/<int:object_id>')
def delete(object_id):
    delete_node(object_id)
    return redirect(url_for('all_storage'))


webview.create_window('Access Control', app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
# webview.settings['ALLOW_DOWNLOADS'] = True
# webview.start()
