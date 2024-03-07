import zlib

from application.templates.xml_template import XMLTemplate


class OfflineTemplate(XMLTemplate):

    def fill_data(self, content, data=None) -> dict:
        content = super().fill_data(content, data)
        check = content.get('CHECK')
        head = check.get('CHECKHEAD')

        OfflineSessionId = 434941
        OfflineSeed = 917269818606292
        OfflineNextLocalNum = 1
        NextLocalNum = head.get('ORDERNUM')
        crc_input = ','.join(
            (
                str(OfflineSeed),
                head.get('ORDERDATE'),
                head.get('ORDERTIME'),
                str(NextLocalNum),
                str(head.get('CASHREGISTERNUM')),
                str(head.get('CASHDESKNUM')),
            )
        )

        crc = str(zlib.crc32(crc_input.encode()))[-4:].lstrip('0')

        ordertaxnum = '{OfflineSessionId}.{OfflineNextLocalNum}.{crc}'.format(
            OfflineSessionId=OfflineSessionId,
            OfflineNextLocalNum=OfflineNextLocalNum,
            crc=crc,
        )

        head['ORDERTAXNUM'] = ordertaxnum

        return content