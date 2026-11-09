import io, zipfile
import graficos as G


def zip_graficos(d):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, fn in G.todos(d).items():
            fig = fn(d); buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
            z.writestr(nome + ".png", buf.getvalue()); G.plt.close(fig)
    return bio.getvalue()
