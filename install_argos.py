from argostranslate import package as p

p.update_package_index()
pkgs = p.get_available_packages()

want = [('ru','en'), ('en','ru'), ('lv','en'), ('en','lv')]
need = [x for x in pkgs if (x.from_code, x.to_code) in want]

print("need:", [(x.from_code, x.to_code) for x in need])

for x in need:
    print("downloading", x.from_code, "->", x.to_code)
    path = x.download()
    print("installing", path)
    p.install_from_path(path)

print("OK")