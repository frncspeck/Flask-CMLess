from flask import Blueprint, render_template, flash, request, redirect, url_for, abort, jsonify
from flask_iam import login_required, role_required, current_user
from flask_wtf import FlaskForm
from wtforms import Form, FormField, FieldList, StringField, EmailField, SubmitField, SelectField, BooleanField, IntegerField, FloatField
from wtforms.validators import InputRequired, Optional, Email
from flask_cmless.models import CModels

primitive_field_types = {
    'Integer': IntegerField,
    'Float': FloatField,
    'Text': StringField,
    'Checkbox': BooleanField
}

class DataTypeForm(Form):
    name = StringField('Field name', validators=[InputRequired()])
    type = SelectField(
        'Type',
        choices = [
            'Integer',
            'Float',
            'Text',
            'Checkbox',
            'Template'
        ],
        validators=[InputRequired()]
    )
    list = BooleanField('As a list')
        
class CMLess:
    DataTypeForm = DataTypeForm # reference in other class, so defined outside

    class DataTemplateForm(FlaskForm):
        name = StringField('Template name', validators=[InputRequired()])
        data_fields = FieldList(FormField(DataTypeForm), min_entries=1)
        additional_field = SubmitField('+ field')
        submit = SubmitField('Create template')
      
    def __init__(self, db, app=None, url_prefix='/cms'):
        self.db = db
        self.url_prefix = url_prefix
        self.models = CModels(db)

        self.blueprint = Blueprint(
            'cms_blueprint', __name__,
            url_prefix=self.url_prefix,
            template_folder='templates'
        )

        self.blueprint.add_url_rule("/", 'create_template', view_func=self.create_template, methods=['GET','POST'])
        self.blueprint.add_url_rule("/template/test/<id>", 'test_template', view_func=self.test_template, methods=['GET','POST'])
        self.blueprint.add_url_rule("/api/add/template", 'create_template_api', view_func=self.create_template_api, methods=['GET','POST'])
        self.blueprint.add_url_rule("/api/add/content/<template_name>", 'create_content_api', view_func=self.add_template_object_api, methods=['GET','POST'])

        if app:
            self.init_app(app)

    def init_app(self, app):
        app.extensions['cms'] = self
        app.register_blueprint(
            self.blueprint, url_prefix=self.url_prefix
        )
        # Set menu
        if 'fefset' in app.extensions:
            fef = app.extensions['fefset']
            fef.add_side_menu_entry(
                'Create data template',
                f"{self.url_prefix}/"
            )#url_for('cms_blueprint.create_template'))        
            fef.add_side_menu_entry(
                'Use data template',
                f"{self.url_prefix}/user/add"
            )#url_for('cms_blueprint.register'))

    @role_required('admin')
    def create_template(self):
        form = self.DataTemplateForm()
        if form.validate_on_submit():
            if form.data['additional_field']:
                form.data_fields.append_entry()
                return render_template('form.html', form=form, title='Create template')
            else:
                # Make model instance
                template = self.models.DataTemplate()
                template.name = form.data['name']
                template.data = form.data['data_fields']
                self.db.session.add(template)
                self.db.session.commit()

                flash("Template was created")

                return redirect('/cms/template/create')
        return render_template('form.html', form=form, title='Create template')

    @login_required
    def create_template_api(self):
        data = request.get_json()
        
        if data:
            if 'name' in data and 'data_fields' in data:
                template = self.models.DataTemplate(
                    name = data['name'],
                    data = data['data_fields']
                )
                self.db.session.add(template)
                self.db.session.commit()
                
                # Return a JSON success message
                return jsonify({"message": "Template was created successfully", "status": "success"}), 201
            else:
                # Return an error message if fields are missing
                return jsonify({"message": "Missing required fields", "status": "error"}), 400
        else:
            # Return an error message if no JSON data is provided
            return jsonify({"message": "Invalid request: No JSON data", "status": "error"}), 400

    @role_required('admin')
    def test_template(self, id):
        title, TemplateRenderedForm = make_template_form(int(id))
        trf = TemplateRenderedForm()
        if trf.validate_on_submit():
            return {
                k:v for k,v in trf.data.items()
                if k not in ('submit', 'csrf_token')
            }
        return render_template('form.html', form=trf, title=title)

    @login_required
    def add_template_object_api(self, template_name):
        data = request.get_json()
        
        if data:
            # Retrieve template
            template = self.models.DataTemplate.query.filter_by(name=template_name).first()
            # TODO check schema and data provide compatible!
            content = self.models.DataObject(
                    template_id = template.id,
                    data = data
            )
            self.db.session.add(content)
            self.db.session.commit()
                
            # Return a JSON success message
            return jsonify({"message": "Content was created successfully", "status": "success"}), 201
        ## Return an error message if fields are missing
        #return jsonify({"message": "Data not compatible with template provided", "status": "error"}), 400
        else:
            # Return an error message if no JSON data is provided
            return jsonify({"message": "Invalid request: No JSON data", "status": "error"}), 400

    
    def make_template_form(self, template_id, formfield=False):
        template = self.models.DataTemplate.query.get_or_404(template_id)
        if formfield:
            class TemplateRenderedForm(Form):
                pass
        else:
            class TemplateRenderedForm(FlaskForm):
                submit = SubmitField(f'Submit "{template.name}"')

        for field in template.data:
            setattr(
                TemplateRenderedForm,
                field['name'].replace(' ','_').lower(),
                # Primitive types
                ((StringField if field['list'] else primitive_field_types[field['type']])(
                    field['name'],
                    validators=([] if field['type'] == 'Checkbox' else [InputRequired()])
                ) if field['type'] in primitive_field_types else (
                # Template types
                FormField(
                    make_template_form(
                        int(field['name'][1:]), formfield=True
                    )[1])
                ))
            )
        return template.name, TemplateRenderedForm

def create_app():
    import os
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_iam import IAM
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config['SECRET_KEY'] = os.urandom(12).hex() # to allow csrf forms
    db = SQLAlchemy()
    db.init_app(app)
    iam = IAM(db, app)
    iam.init_app(app)
    cmless = CMLess(db, app)
    with app.app_context():
        db.create_all()
    return app
