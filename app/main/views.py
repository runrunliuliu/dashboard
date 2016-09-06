from flask import render_template, redirect, url_for, flash, request, abort, \
    current_app, jsonify
from flask_login import current_user, login_required
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, \
    EditHoldsForm, EditDropsForm, EditStopWinForm
from .. import db
from ..models import Permission, Role, User, Post, Firm, Company, FirmTier, \
    FirmType, Follow, Geo, UserType, Stock, Tbuy, Holds
from ..decorators import admin_required, permission_required
import datetime
import json


@main.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_anonymous:
        return redirect(url_for('auth.login'))
    else:
        top_vc_firms = current_user.top_firms(n=10, firm_type_code='vc')
        top_ai_firms = current_user.top_firms(n=10, firm_type_code='ai')
        top_su_firms = current_user.top_firms(n=10, firm_type_code='su')
        # return render_template('index.html', top_vc_firms=top_vc_firms,
        #                        top_ai_firms=top_ai_firms,
        #                        top_su_firms=top_su_firms)
        return redirect(url_for('main.tbuy'))


@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.outerjoin(Geo).outerjoin(UserType)\
        .with_entities(User, Geo, UserType)\
        .filter(User.username==username).first_or_404()

    # query for firms
    firms = Firm.query.join(FirmType).join(FirmTier).join(User)\
        .with_entities(Firm, FirmType, FirmTier, User)\
        .filter(User.username == username)\
        .order_by(FirmTier.firm_tier.asc(), Firm.name.asc()).all()

    # parse firms
    vc_firms = []
    ai_firms = []
    su_firms = []
    for firm in firms:
        if firm.FirmType.firm_type_code == 'vc':
            vc_firms.append(firm)
        if firm.FirmType.firm_type_code == 'ai':
            ai_firms.append(firm)
        if firm.FirmType.firm_type_code == 'su':
            su_firms.append(firm)

    return render_template('user.html', user=user, vc_firms=vc_firms,
                           ai_firms=ai_firms, su_firms=su_firms)

@main.route('/stocks')
@login_required
def stocks():
    results = Stock.query.order_by(Stock.stockid.asc()).all()
    stocks  = [{'stock': item, 'timestamp': None}
                 for item in results]
    return render_template('stock_list.html', stocks=stocks)

@main.route('/tdrops')
@login_required
def tdrops():
    filters = Holds.query.filter(Holds.status == 2)
    results = filters.join(Stock, Stock.stockid == Holds.stockid) \
                .add_columns(
                    Holds.stockid,
                    Stock.stockname,
                    Holds.strategyid,
                    Holds.reason,
                    Holds.dreason,
                    Holds.sigday,
                    Holds.sellday,
                    Holds.bprice,
                    Holds.nprice,
                    Holds.sprice,
                    Holds.holds,) \
                .order_by(Holds.strategyid.asc(), Holds.id.asc()).all()
    drops    = [
                {
                    'drop': item,
                    'timestamp': None
                }
                for item in results
              ]
    return render_template('drops_list.html', drops=drops)

@main.route('/gholds')
def gholds():
    celue   = request.args.get('cl')
    filters = Holds.query.filter(Holds.status == 1).all()
    res = {}
    stocks = []
    for item in filters:
        stocks.append(item.stockid)

    res['cl']     = celue
    res['stocks'] = stocks

    return json.dumps(res)

@main.route('/tholds')
@login_required
def tholds():
    celue = request.args.get('cl')
    if celue is not None:
        filters = Holds.query.filter(Holds.status == 1)
        filters = filters.filter(Holds.strategyid == celue)
    else:
        filters = Holds.query.filter(Holds.status == 1)

    results = filters.join(Stock, Stock.stockid == Holds.stockid) \
                .add_columns(
                    Holds.id,
                    Holds.stockid,
                    Stock.stockname,
                    Holds.strategyid,
                    Holds.reason,
                    Holds.dreason,
                    Holds.buyday,
                    Holds.sellday,
                    Holds.bprice,
                    Holds.nprice,
                    Holds.sprice,
                    Holds.holds,) \
                .order_by(Holds.strategyid.asc(), Holds.id.asc()).all()
    holds    = [
                {
                    'hold': item,
                    'ret': float('{0:.4f}'.format((item.nprice - item.bprice) / item.bprice * 100)),
                    'timestamp': None
                }
                for item in results
              ]
    return render_template('holds_list.html', holds=holds)

@main.route('/tfinish')
@login_required
def tfinish():
    filters = Holds.query.filter(Holds.status == 3)
    results = filters.join(Stock, Stock.stockid == Holds.stockid) \
                .add_columns(
                    Holds.id,
                    Holds.stockid,
                    Stock.stockname,
                    Holds.strategyid,
                    Holds.reason,
                    Holds.buyday,
                    Holds.sellday,
                    Holds.bprice,
                    Holds.nprice,
                    Holds.sprice,
                    Holds.oprice,
                    Holds.holds,) \
                .order_by(Holds.strategyid.asc(), Holds.id.asc()).all()
    holds    = [
                {
                    'hold': item,
                    'ret': float('{0:.2f}'.format((item.sprice - item.bprice) / item.bprice * 100)),
                    'bslip': float('{0:.2f}'.format((item.bprice - item.oprice) / item.oprice * 100)),
                    'sslip': float('{0:.2f}'.format((item.sprice - item.nprice) / item.bprice * 100)),
                    'timestamp': None
                }
                for item in results
              ]
    return render_template('finish_list.html', holds=holds)

@main.route('/tbuys')
@login_required
def tbuy():
    day   = request.args.get('day')
    celue = request.args.get('cl')
    if day is not None and celue is not None:
        filters = Tbuy.query.filter(Tbuy.day == day)
        filters = filters.filter(Tbuy.strategyid == celue)
    else:
        filters = Tbuy.query.filter(Tbuy.day != '')

    distdays = []
    days = db.session.query(Tbuy.day).distinct().all()
    for d in days:
        distdays.append(d[0])
    sortdays = sorted(distdays, key=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'), reverse=True)

    results = filters.join(Stock, Stock.stockid == Tbuy.stockid) \
                .add_columns(Tbuy.id, Tbuy.stockid, Stock.stockname, Tbuy.strategyid \
                , Tbuy.reason, Tbuy.blow, Tbuy.bhigh, Tbuy.day, Tbuy.act) \
                .order_by(Tbuy.day.desc(), Tbuy.strategyid.asc(), Tbuy.id.asc()).all()
    buys    = [
                {
                    'buy': item,
                    'timestamp': None
                }
                for item in results
              ]
    return render_template('tbuy_list.html', buys=buys, sdays=sortdays)


@main.route('/users/<username>')
@login_required
def users(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))

    # get request arguments
    followed = request.args.get('followed', 1, type=int)

    # query for users
    if followed:
        results = user.followed.order_by(Follow.timestamp.desc()).all()
        users = [{'user': item.followed, 'timestamp': item.timestamp}
                 for item in results]
    else:
        results = User.query.order_by(User.username.asc()).all()
        users = [{'user': item, 'timestamp': None}
                 for item in results]

    return render_template('user_list.html', user=user, users=users,
                           followed=followed)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        # change values based on form input
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        current_user.geo = Geo.query.get(form.geo.data)
        current_user.user_type = UserType.query.get(form.user_type.data)
        db.session.add(current_user)
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('main.user', username=current_user.username))
    # set inital values
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    form.geo.data = current_user.geo_id
    form.user_type.data = current_user.user_type_id
    return render_template('edit_profile.html', form=form)

@main.route('/edit_stopwin/<int:id>', methods=['GET', 'POST'])
def edit_stopwin(id):
    hold  = Holds.query.get_or_404(id)
    form = EditStopWinForm(user=user)
    if form.validate_on_submit():
        setattr(hold, 'sellday', form.sday.data)
        setattr(hold, 'sprice', form.sprice.data)
        setattr(hold, 'status', 3)
        db.session.commit()
        flash('The profile has been updated.', 'success')
        return redirect(url_for('main.tholds'))
    return render_template('edit_stopwin.html', form=form, user=user)

@main.route('/edit_upholds/<int:id>', methods=['GET', 'POST'])
def edit_upholds(id):
    buy  = Tbuy.query.get_or_404(id)
    buy.act = 1
    db.session.commit()

    form = EditHoldsForm(user=user)
    if form.validate_on_submit():
        f = Holds(
                stockid    = buy.stockid,
                strategyid = buy.strategyid,
                reason     = buy.reason,
                sellday    = '',
                bprice     = form.price.data,
                buyday     = form.bday.data,
                oprice     = form.oprice.data,
                nprice     = -1,
                holds      = 0,
                status     = 1,)
        db.session.add(f)
        flash('The profile has been updated.', 'success')
        return redirect(url_for('main.tbuy'))
    return render_template('edit_upholds.html', form=form, user=user)

@main.route('/edit_updrops/<int:id>', methods=['GET', 'POST'])
def edit_updrops(id):
    buy = Tbuy.query.get_or_404(id)
    buy.act = 1
    db.session.commit()
    form = EditDropsForm(user=user)
    if form.validate_on_submit():
        f = Holds(
                stockid    = buy.stockid,
                strategyid = buy.strategyid,
                reason     = buy.reason,
                dreason    = form.dreason.data,
                sigday     = form.tday.data,
                bprice     = form.oprice.data,
                nprice     = -1,
                status     = 2,)
        db.session.add(f)
        flash('The profile has been updated.', 'success')
        return redirect(url_for('main.tbuy'))
    return render_template('edit_updrops.html', form=form, user=user)

@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.geo = Geo.query.get(form.geo.data)
        user.user_type = UserType.query.get(form.user_type.data)
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.', 'success')
        return redirect(url_for('main.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.geo.data = user.geo_id
    form.user_type.data = user.user_type_id
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>')
@login_required
def post(id):
    post = Post.query.get_or_404(id)
    return render_template('post.html', posts=[post])


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('The post has been updated.', 'success')
        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))
    if current_user.is_following(user):
        flash('You are already following this user.', 'error')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username, 'success')
    return redirect(url_for('main.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.', 'error')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username, 'success')
    return redirect(url_for('main.user', username=username))


@main.route('/followers/<username>')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='main.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
@login_required
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='main.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/company/<int:id>')
@login_required
def company(id):
    company = Company.query.join(User).filter(Company.id == id).first()
    if company is None:
        flash('Company Does Not Exist.', 'error')
        return redirect(url_for('main.index'))
    vc_firms = company.related_firms('vc')
    ai_firms = company.related_firms('ai')
    su_orgs = company.related_firms('su')
    return render_template('startup.html', company=company, vc_firms=vc_firms,
                           ai_firms=ai_firms, su_orgs=su_orgs)


@main.route('/companies/<username>')
@login_required
def companies(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))

    # get request arguments
    filter_user = request.args.get('filter_user', 1, type=int)

    # query for companies
    query = Company.query
    if filter_user:
        query = query.filter(Company.user_id == user.id)
    query = query.order_by(Company.name.asc())

    # build response dataset
    company_list = query.all()
    companies = [{'id': item.id,
                  'name': item.name,
                  'owner': item.owner,
                  'city': item.city,
                  'state': item.state,
                  'country': item.country}
                 for item in company_list]
    return render_template('startup_list.html', user=user,
                           filter_user=filter_user, companies=companies)


@main.route('/firm/<int:id>')
@login_required
def firm(id):
    firm = Firm.query\
        .join(FirmType).join(FirmTier).join(User)\
        .filter(Firm.id == id).first()
    if firm is None:
        flash('Relationship Does Not Exist.', 'error')
        return redirect(url_for('main.index'))
    companies = firm.related_companies()
    return render_template('firm.html', firm=firm, companies=companies)


@main.route('/firms/<username>')
@login_required
def firms(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))

    # get request arguments
    firm_type_code = request.args.get('firm_type_code', 'vc', type=str)
    filter_user = request.args.get('filter_user', 1, type=int)

    # format firm type
    firm_type = FirmType.query.filter_by(firm_type_code=firm_type_code).first()
    from inflect import engine
    p = engine()
    firm_type_full = firm_type.firm_type
    firm_type_code = firm_type.firm_type_code
    firm_type_p = p.plural(firm_type_full)

    # query for firms
    query = Firm.query\
        .join(FirmType, FirmType.id == Firm.firm_type_id)\
        .join(FirmTier, FirmTier.id == Firm.firm_tier_id)\
        .filter(FirmType.firm_type == firm_type_full)
    if filter_user:
        query = query.filter(Firm.user_id == user.id)
    query = query.order_by(FirmTier.firm_tier.asc(), Firm.name.asc())

    # build response dataset
    firm_list = query.all()
    firms = [{'id': item.id,
              'name': item.name,
              'type': item.type.firm_type,
              'tier': item.tier.firm_tier,
              'owner': item.owner,
              'city': item.city,
              'state': item.state,
              'country': item.country}
             for item in firm_list]
    return render_template('firm_list.html', user=user,
                           title=firm_type_p, type_code=firm_type_code,
                           filter_user=filter_user, endpoint='main.firms',
                           firms=firms)
