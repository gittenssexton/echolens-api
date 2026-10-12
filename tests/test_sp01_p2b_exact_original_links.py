import unittest
from scripts.sp01_p2b_exact_original_links import exact_original_links

V='http://www.ivoa.net/xml/VOTable/v1.3'

def xml_for(visit,wrong=False):
    fields=''.join(f'<FIELD name="{k}" />' for k in ['ID','access_url','description','content_type'])
    rows=[]
    for i in (1,2,3,4):
        name=f'{visit}{i}.fits'
        url=f'https://datacentral.org.au/services/sov/1/download/galah.dr4.spectra.hermes.spectrum_1d/{name}'
        if wrong and i==2:url='https://evil.example/services/sov/'+name
        rows.append('<TR>'+''.join(f'<TD>{v}</TD>' for v in [visit,url,'FITS spectrum (original)','application/fits'])+'</TR>')
    return f'<VOTABLE xmlns="{V}"><RESOURCE><INFO name="QUERY_STATUS" value="OK"/><TABLE>{fields}<DATA><TABLEDATA>{"".join(rows)}</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'.encode()

class Tests(unittest.TestCase):
    def test_all_four_exact(self):
        links=exact_original_links(xml_for('151111003101245'),'151111003101245')
        self.assertEqual(set(links),{'B','G','R','I'})
    def test_reject_foreign_host(self):
        with self.assertRaisesRegex(ValueError,'Not exactly 4'):
            exact_original_links(xml_for('151111003101245',True),'151111003101245')
    def test_reject_mismatched_target(self):
        with self.assertRaisesRegex(ValueError,'Not exactly 4'):
            exact_original_links(xml_for('151111003101245'),'221003001101138')
if __name__=='__main__':unittest.main()
