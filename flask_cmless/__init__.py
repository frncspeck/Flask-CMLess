from flask import Blueprint, render_template, flash, request, redirect, url_for, abort
from flask_iam import role_required, current_user
from flask_wtf import FlaskForm
from wtforms import Form, FormField, FieldList, StringField, EmailField, SubmitField, SelectField, BooleanField, IntegerField, FloatField
from wtforms.validators import InputRequired, Optional, Email

primitive_field_types = {
    'Integer': IntegerField,
    'Float': FloatField,
    'Text': StringField,
    'Checkbox': BooleanField
}

#from flask_cmless.models import DataTemplate
class DataTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    data = db.Column(db.JSON)

class CMLess:
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

    class DataTemplateForm(FlaskForm):
        name = StringField('Template name', validators=[InputRequired()])
        required_field = FieldList(FormField(DataTypeForm), min_entries=1)
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

    def init_app(self, app):
        app.extensions['cms'] = self
        app.register_blueprint(
            self.blueprint, url_prefix=self.url_prefix
        )
        # Set menu
        fef = app.extensions['fefset']
        fef.add_side_menu_entry('Create data template', f"{self.url_prefix}/")#url_for('cms_blueprint.create_template'))        
        fef.add_side_menu_entry('Use data template', f"{self.url_prefix}/user/add")#url_for('cms_blueprint.register'))

    @role_required('admin')
    def create_template(self):
        form = DataTemplateForm()
        if form.validate_on_submit():
            if form.data['additional_field']:
                form.required_field.append_entry()
                return render_template('form.html', form=form, title='Create template')
            else:
                # Make model instance
                template = DataTemplate()
                template.name = form.data['name']
                template.data = form.data['required_field']
                self.db.session.add(template)
                self.db.session.commit()

                flash("Template was created")

                return redirect('/cms/template/create')
        return render_template('form.html', form=form, title='Create template')

    @role_required
    def test_template(self, id):
        title, TemplateRenderedForm = make_template_form(int(id))
        trf = TemplateRenderedForm()
        if trf.validate_on_submit():
            return {
                k:v for k,v in trf.data.items()
                if k not in ('submit', 'csrf_token')
            }
        return render_template('form.html', form=trf, title=title)

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
