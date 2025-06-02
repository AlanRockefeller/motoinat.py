import unittest
from unittest.mock import patch, mock_open
import sys
import io # Required for capturing print output

# Assuming motoinat.py is in the same directory or accessible via PYTHONPATH
import motoinat

class TestMotoInat(unittest.TestCase):

    @patch('motoinat.requests.get')
    def test_find_inaturalist_observation_found(self, mock_get):
        # Mock the API response for a successful find
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        # Ensure raise_for_status does nothing for 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'total_results': 1,
            'results': [{
                'id': 12345,
                'species_guess': 'Amanita muscaria',
                'place_guess': 'California, USA'
            }]
        }

        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        motoinat.find_inaturalist_observation('67890', debug_mode=False, url_only=False, number_only=False)
        
        sys.stdout = sys.__stdout__  # Reset stdout
        output = captured_output.getvalue()

        self.assertIn("Mushroom Observer #67890:", output)
        self.assertIn("iNaturalist Observation: https://www.inaturalist.org/observations/12345", output)
        self.assertIn("Species: Amanita muscaria", output)
        self.assertIn("Location: California, USA", output)
        # Check one of the MO URLs to ensure it's part of the search logic (and thus matched_url)
        # The script tries multiple URL formats. We need to ensure the one that would be formed is checked.
        # The _fetch_inat_data is called with different mo_url. The _format_and_print_observation receives the matched one.
        # Let's assume the first one matches for simplicity in this test, or pick one from the list.
        # The first one is f"http://mushroomobserver.org/observer/show_observation/{mo_number}"
        # However, the test data in problem description uses https://mushroomobserver.org/67890
        # Let's stick to what the problem description had for assertion.
        self.assertIn(f"Matched URL: http://mushroomobserver.org/observer/show_observation/67890", output)


    @patch('motoinat.requests.get')
    def test_find_inaturalist_observation_not_found(self, mock_get):
        # Mock the API response for no results found
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'total_results': 0, 'results': []}
        
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        motoinat.find_inaturalist_observation('00000', debug_mode=False, url_only=False, number_only=False)
        
        sys.stdout = sys.__stdout__ # Reset stdout
        output = captured_output.getvalue()

        self.assertIn("No iNaturalist observation found for Mushroom Observer #00000", output)

    @patch('motoinat.requests.get')
    def test_find_inaturalist_observation_url_only(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'total_results': 1,
            'results': [{'id': 12345}]
        }
        
        captured_output = io.StringIO()
        sys.stdout = captured_output

        motoinat.find_inaturalist_observation('67890', debug_mode=False, url_only=True, number_only=False)
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue().strip()

        self.assertEqual(output, "https://www.inaturalist.org/observations/12345")

    @patch('motoinat.requests.get')
    def test_find_inaturalist_observation_number_only(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'total_results': 1,
            'results': [{'id': 12345}]
        }

        captured_output = io.StringIO()
        sys.stdout = captured_output

        motoinat.find_inaturalist_observation('67890', debug_mode=False, url_only=False, number_only=True)
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue().strip()
        
        self.assertEqual(output, "12345")
        
    @patch('motoinat.requests.get')
    def test_api_error_handling(self, mock_get):
        # Simulate an API error (e.g., 500 server error or network issue)
        # This will be caught by _fetch_inat_data which returns None
        mock_get.side_effect = motoinat.requests.exceptions.RequestException("Test API error")

        captured_output = io.StringIO()
        sys.stdout = captured_output # Capture potential prints
        
        # Suppress logging output for this test to keep stdout clean for assertion
        # and to check if logging.warning was called as intended.
        with patch('motoinat.logging') as mock_logging:
             motoinat.find_inaturalist_observation('11111', debug_mode=False, url_only=False, number_only=False)

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        # Check that the "not found" message is printed as a fallback
        self.assertIn("No iNaturalist observation found for Mushroom Observer #11111", output)
        # Check that a warning was logged for each URL tried (6 URLs)
        self.assertEqual(mock_logging.warning.call_count, 6)


    # Basic test for argument parsing and main function flow (file input)
    @patch('motoinat.find_inaturalist_observation') # Mock the core function
    @patch('builtins.open', new_callable=mock_open, read_data="123\n456\n") # Added trailing newline
    def test_main_with_file_input(self, mock_file_open, mock_find_obs):
        test_args = ['motoinat.py', '--file', 'dummy.txt']
        # Mock args.debug, args.url, args.q which are accessed in main
        # This can be done by patching argparse if needed, or by ensuring defaults
        # For simplicity, find_inaturalist_observation is mocked, so its args are checked
        with patch.object(sys, 'argv', test_args):
            motoinat.main()
        
        self.assertEqual(mock_find_obs.call_count, 2)
        # The main function passes args.debug, args.url, args.q
        # Default values from argparse are: debug=False, url=False, q=False
        mock_find_obs.assert_any_call('123', False, False, False)
        mock_find_obs.assert_any_call('456', False, False, False)

    @patch('motoinat.find_inaturalist_observation') # Mock the core function
    def test_main_with_arg_input_and_invalid(self, mock_find_obs):
        captured_stderr = io.StringIO()
        sys.stderr = captured_stderr

        test_args = ['motoinat.py', '123', 'abc', '456']
        with patch.object(sys, 'argv', test_args):
            motoinat.main()
        
        sys.stderr = sys.__stderr__ 
        stderr_output = captured_stderr.getvalue()

        self.assertIn("Warning: Invalid MO number 'abc' provided. Skipping.", stderr_output)
        self.assertEqual(mock_find_obs.call_count, 2)
        mock_find_obs.assert_any_call('123', False, False, False) 
        mock_find_obs.assert_any_call('456', False, False, False)

if __name__ == '__main__':
    unittest.main()
