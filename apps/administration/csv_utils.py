import csv
from decimal import Decimal, InvalidOperation

from django.http import StreamingHttpResponse


class Echo:
    def write(self, value):
        return value


def safe_csv_text(value):
    text = '' if value is None else str(value)
    try:
        Decimal(text)
        return text
    except (InvalidOperation, TypeError, ValueError):
        pass
    if text.startswith(('=', '+', '-', '@', '\t', '\r')):
        return f"'{text}"
    return text


def stream_csv(rows, filename):
    writer = csv.writer(Echo())

    def generate():
        yield '\ufeff'
        for row in rows:
            yield writer.writerow([
                value if isinstance(value, (int, float)) else safe_csv_text(value)
                for value in row
            ])

    response = StreamingHttpResponse(generate(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
