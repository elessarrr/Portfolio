# Script to convert Excel data to Parquet format with detailed logging
import sys
import logging
from utils.data_preprocessor import DataPreprocessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    try:
        logging.info('Starting data conversion from Excel to Parquet...')
        preprocessor = DataPreprocessor()
        preprocessor.convert_to_parquet()
        logging.info('Data conversion completed successfully!')
        return 0
    except Exception as e:
        logging.error(f'Failed to convert data: {str(e)}')
        return 1

if __name__ == '__main__':
    sys.exit(main())