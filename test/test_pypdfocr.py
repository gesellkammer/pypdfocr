#from pypdfocr import PyPDFOCR as P
import pypdfocr.pypdfocr as P
import pytest
import os

from PyPDF2 import PdfFileReader
import smtplib
from mock import Mock
from mock import patch, call


class TestPydfocr:

    def setup(self):
        self.p = P.PyPDFOCR()

    def _iter_pdf(self, filename):
        reader = PdfFileReader(filename)
        for pgnum in range(reader.getNumPages()):
            text = reader.getPage(pgnum).extractText()
            text = text.encode('ascii', 'ignore')
            text = text.replace('\n', ' ')
            yield text
    
    pdf_tests = [
            (".", "temp/target/recipe", "../test/pdfs/test_recipe.pdf", [ ["Spinach Recipe","Drain any excess"],
                                 ]),
        (".", "temp/target/patents", "pdfs/test_patent.pdf", [ 
                           ["ASYNCHRONOUS", "subject to a", "20 Claims"], # Page 1
                           ["FOREIGN PATENT" ], # Page 2
                            ]),
        (".", "temp/target/default", "pdfs/test_sherlock.pdf", [ ["Bohemia", "Trincomalee"], # Page 1
                           ["hundreds of times" ], # Page 2
                           ]),
        ("pdfs", "temp/target/default", "test_sherlock.pdf", [ ["Bohemia", "Trincomalee"], # Page 1
                           ["hundreds of times" ], # Page 2
                           ]),
        ]

    #@pytest.mark.skipif(True, reason="Just testing")
    @pytest.mark.parametrize("dirname, tgt_folder, filename, expected", pdf_tests)
    def test_standalone(self, dirname, tgt_folder, filename, expected):
        """
            :param expected: List of keywords lists per page.  expected[0][1] is the second keyword to assert on page 1
        """
        # Run a single file conversion
        cwd = os.getcwd()
        os.chdir(dirname)
        opts = [filename]
        self.p.go(opts)

        out_filename = filename.replace(".pdf", "_ocr.pdf")
        assert(os.path.exists(out_filename))
        for i,t in enumerate(self._iter_pdf(out_filename)):
            if len(expected) > i:
                for keyword in expected[i]:
                    assert(keyword in t)
            print ("\n----------------------\nPage %d\n" % i)
            print t
        os.remove(out_filename)
        os.chdir(cwd)

    #@pytest.mark.skipif(True, reason="just testing")
    @pytest.mark.parametrize("dirname, tgt_folder, filename, expected", [pdf_tests[0]])
    def test_standalone_email(self, dirname, tgt_folder, filename, expected):
        # Run a single file conversion

        # Mock the smtplib to test the email functions
        #smtplib.SMTP = Mock('smtplib.SMTP')
        #smtplib.SMTP.mock_returns = Mock('smtp_connection')
        with patch("smtplib.SMTP") as mock_smtp:
            cwd = os.getcwd()
            os.chdir(dirname)
            opts = [filename, "--config=test_pypdfocr_config.yaml", "-m"]
            self.p.go(opts)

            out_filename = filename.replace(".pdf", "_ocr.pdf")
            assert(os.path.exists(out_filename))
            for i,t in enumerate(self._iter_pdf(out_filename)):
                if len(expected) > i:
                    for keyword in expected[i]:
                        assert(keyword in t)
                print ("\n----------------------\nPage %d\n" % i)
                print t
            os.remove(out_filename)
            os.chdir(cwd)
            
            # Assert the smtp calls
            instance = mock_smtp.return_value
            assert(instance.starttls.called)
            instance.login.assert_called_once_with("someone@gmail.com", "blah")
            assert(instance.sendmail.called)

    @patch('shutil.move')
    @pytest.mark.parametrize("config", [("test_pypdfocr_config.yaml"), ("test_pypdfocr_config_no_move_original.yaml")])
    @pytest.mark.parametrize("dirname, tgt_folder, filename, expected", pdf_tests[0:3])
    def test_standalone_filing(self, mock_move, config, dirname, tgt_folder, filename, expected):
        # Run a single file conversion

        # Mock the move function so we don't actually end up filing
        cwd = os.getcwd()
        if os.path.exists("temp"):
            os.chdir("temp")
            for d in ['target/patents', 'target/recipe']:
                if os.path.exists(d):
                    os.removedirs(d)
            os.chdir(cwd)

        os.chdir(dirname)
        #opts = [filename, "--config=test_pypdfocr_config.yaml", "-f"]
        opts = [filename, "--config=%s" % config, "-f"]
        self.p.go(opts)

        out_filename = filename.replace(".pdf", "_ocr.pdf")
        assert(os.path.exists(out_filename))
        for i,t in enumerate(self._iter_pdf(out_filename)):
            if len(expected) > i:
                for keyword in expected[i]:
                    assert(keyword in t)
            print ("\n----------------------\nPage %d\n" % i)
            print t
        os.remove(out_filename)
        os.chdir(cwd)
        
        # Assert the smtp calls
        calls = [call(out_filename,
                        os.path.abspath(os.path.join(tgt_folder,os.path.basename(out_filename))))]
        if not "no_move_original" in config:
            new_file_name = os.path.basename(filename).replace(".pdf", "_2.pdf")
            calls.append(call(filename,
                                os.path.abspath(os.path.join("temp/original", new_file_name))))
        mock_move.assert_has_calls(calls)
            #assert(instance.starttls.called)
            #instance.login.assert_called_once_with("someone@gmail.com", "blah")
            #assert(instance.sendmail.called)
