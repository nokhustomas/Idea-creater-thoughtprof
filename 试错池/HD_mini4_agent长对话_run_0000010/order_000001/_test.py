import sys
sys.path.insert(0, '.')
import app
print('import ok')
print('has page_home:', hasattr(app, 'page_home'))
print('has page_about:', hasattr(app, 'page_about'))
print('has page_members:', hasattr(app, 'page_members'))
print('has page_resource:', hasattr(app, 'page_resource'))
print('has admin_home:', hasattr(app, 'admin_home'))
print('has admin_edit:', hasattr(app, 'admin_edit'))
