from io import BytesIO

from PIL import Image


def copy_fig_to_clipboard(fig):
    import win32clipboard

    """
    pip install winclip32 pillow
    """
    # figure -> BytesIO
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)

    # BytesIO -> Pillow
    image = Image.open(buf)

    # Convert data
    output = BytesIO()
    image.save(output, "BMP")
    data = output.getvalue()[14:]  # remove BMP header
    output.close()

    # Copy to clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()
