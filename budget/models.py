from collections import defaultdict

from datetime import datetime
from flaskext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# define models
class Project(db.Model):
    id = db.Column(db.String, primary_key=True)

    name = db.Column(db.UnicodeText)
    password = db.Column(db.String)
    contact_email = db.Column(db.String)
    members = db.relationship("Person", backref="project")

    @property
    def active_members(self):
        return [m for m in self.members if m.activated]

    def get_balance(self):

        balances, should_pay, should_receive = defaultdict(int), defaultdict(int), defaultdict(int)

        # for each person
        for person in self.members:
            # get the list of bills he has to pay
            bills = Bill.query.filter(Bill.owers.contains(person))
            for bill in bills.all():
                if person != bill.payer: 
                    should_pay[person] += bill.pay_each()
                    should_receive[bill.payer] += bill.pay_each()

        for person in self.members:
            balances[person] = should_receive[person] - should_pay[person]

        return balances

    def get_bills(self):
        """Return the list of bills related to this project"""
        return Bill.query.join(Person, Project)\
            .filter(Bill.payer_id == Person.id)\
            .filter(Person.project_id == Project.id)\
            .filter(Project.id == self.id)\
            .order_by(Bill.date.desc())

    def remove_member(self, member_id):
        """Remove a member from the project.

        If the member is not bound to a bill, then he is deleted, otherwise
        he is only deactivated.

        This method returns the status DELETED or DEACTIVATED regarding the
        changes made.
        """
        person = Person.query.get_or_404(member_id)
        if person.project == self:
            if not person.has_bills():
                db.session.delete(person)
                db.session.commit()
            else:
                person.activated = False
                db.session.commit()
        return person

    def __repr__(self):
        return "<Project %s>" % self.name


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    bills = db.relationship("Bill", backref="payer")

    name = db.Column(db.UnicodeText)
    activated = db.Column(db.Boolean, default=True)

    def has_bills(self):
        bills_as_ower_number = db.session.query(Bill).join(billowers, Person)\
            .filter("Bill.id == billowers.bill_id")\
            .filter("Person.id == billowers.person_id")\
            .filter(Person.id == self.id)\
            .count()
        return bills_as_ower_number != 0 or len(self.bills) != 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Person %s for project %s>" % (self.name, self.project.name)

# We need to manually define a join table for m2m relations
billowers = db.Table('billowers',
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id')),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id')),
)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    payer_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    owers = db.relationship(Person, secondary=billowers)

    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.now)
    what = db.Column(db.UnicodeText)

    archive = db.Column(db.Integer, db.ForeignKey("archive.id"))

    def pay_each(self):
        """Compute what each person has to pay"""
        return round(self.amount / len(self.owers), 2)

    def __repr__(self):
        return "<Bill of %s from %s for %s>" % (self.amount,
                self.payer, ", ".join([o.name for o in self.owers]))


class Archive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    name = db.Column(db.UnicodeText)

    @property
    def start_date(self):
        pass

    @property
    def end_date(self):
        pass

    def __repr__(self):
        return "<Archive>"