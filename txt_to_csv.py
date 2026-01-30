import pandas as pd

column_names = [
    'CMTE_ID', 'AMNDT_IND', 'RPT_TP', 'TRANSACTION_PGI', 'IMAGE_NUM',
    'TRANSACTION_TP', 'ENTITY_TP', 'NAME', 'CITY', 'STATE', 'ZIP_CODE',
    'EMPLOYER', 'OCCUPATION', 'TRANSACTION_DT', 'TRANSACTION_AMT',
    'OTHER_ID', 'TRAN_ID', 'FILE_NUM', 'MEMO_CD', 'MEMO_TEXT', 'SUB_ID'
]

print("Reading pipe-delimited file...")
df = pd.read_csv('itcont.txt', sep='|', header=None, names=column_names)

print("Saving to itcont.csv...")
df.to_csv('itcont.csv', index=False)
