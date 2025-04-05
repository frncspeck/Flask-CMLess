class CModels(object):
    def __init__(self, db):
        self.db = db
        self._make_models()
    
    def _make_models(self):
        db = self.db
        
        class DataTemplate(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String, unique=True)
            data = db.Column(db.JSON)
        self.DataTemplate = DataTemplate

        class DataObject(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            template_id = db.Column(db.Integer, db.ForeignKey("data_template.id"))
            template = self.db.relationship(
                'DataTemplate' #, back_populates='instances'
            )
            data = db.Column(db.JSON)
        self.DataObject = DataObject

