```text
S1 E - Condition:
    ( Time ( 'NSE' ) >= Number ( '1515' ) )
S1 E - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Buy	NIFTY 50	( Get Strike ( 'NIFTY 50', LTP (  ) ) + Get Runtime ( 'HedgeGap' ) )	CE	tt_curr_monthexpiry('NIFTY 50')	1	
    Buy	NIFTY 50	( Get Strike ( 'NIFTY 50', LTP (  ) ) - Get Runtime ( 'HedgeGap' ) )	PE	tt_curr_monthexpiry('NIFTY 50')	1	
S1 R - Condition:
    ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '1', '1' ) != Number ( '0' ) )
S1 R - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	ATM	CE	tt_curr_monthexpiry('NIFTY 50')	1	
    Sell	NIFTY 50	ATM	PE	tt_curr_monthexpiry('NIFTY 50')	1	
S1 R - Condition:
    ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '4', '1' ) > Number ( '0' ) AND Net Quantity ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '1', '1' ) ) != Number ( '0' ) )
S1 R - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '1' ) )	CE	tt_curr_monthexpiry('NIFTY 50')	1	
S1 R - Condition:
    ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '4', '1' ) > Number ( '0' ) AND Net Quantity ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '1', '2' ) ) != Number ( '0' ) )
S1 R - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '2' ) )	PE	tt_curr_monthexpiry('NIFTY 50')	1	

S2 E - Condition:
    ( LTP ( Instrument Name ( 'NFO,NIFTY 50,Current Month,,,,' ) ) > Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '1' ) )
S2 E - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '1' ) )	CE	tt_curr_monthexpiry('NIFTY 50')	1	
    Buy	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '1' ) + Get Runtime ( 'HedgeRoll' ) )	CE	tt_curr_monthexpiry('NIFTY 50')	1	
S2 R - Condition:
    ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '4', '1' ) > Number ( '0' ) AND Net Quantity ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '2', '2' ) ) != Number ( '0' ) )
S2 R - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '2', '2' ) )	CE	tt_curr_monthexpiry('NIFTY 50')	1	

S3 E - Condition:
    ( LTP ( Instrument Name ( 'NFO,NIFTY 50,Current Month,,,,' ) ) < Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '2' ) )
S3 E - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '2' ) )	PE	tt_curr_monthexpiry('NIFTY 50')	1	
    Buy	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '1', '2' ) - Get Runtime ( 'HedgeRoll' ) )	PE	tt_curr_monthexpiry('NIFTY 50')	1	
S3 R - Condition:
    ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '4', '1' ) > Number ( '0' ) AND Net Quantity ( Traded Instrument ( 'Entry', 'quantity', 'NIFTY 50', '1', '3', '2' ) ) != Number ( '0' ) )
S3 R - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Sell	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '3', '2' ) )	PE	tt_curr_monthexpiry('NIFTY 50')	1	

S4 E - Condition:
    ( Get Runtime ( 'HOLD_TILL_EXPIRY' ) == Number ( '1' ) AND Days to Expiry ( 'NIFTY 50' ) < Number ( '7' ) )
S4 E - Positions
    Action	Underlying	Strike	Type	Expiry	Qty	Price
    Buy	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '2', '1' ) + Get Runtime ( 'HedgeRoll' ) )	CE	tt_curr_monthexpiry('NIFTY 50')	1	
    Buy	NIFTY 50	( Traded Instrument ( 'Entry', 'strike', 'NIFTY 50', '1', '2', '2' ) - Get Runtime ( 'HedgeRoll' ) )	PE	tt_curr_monthexpiry('NIFTY 50')	1	

Universal Exit - Condition:
    ( ( Get Runtime ( 'HOLD_TILL_EXPIRY' ) == Number ( '0' ) AND Days to Expiry ( 'NIFTY 50' ) < Number ( '7' ) ) OR ( Get Runtime ( 'HOLD_TILL_EXPIRY' ) == Number ( '1' ) AND Days to Expiry ( 'NIFTY 50' ) == Number ( '0' ) ) )

```
