Run time: 05/04/2026 10:21:08

Json query: {"ExportFormat":"data","ResultSetSize":500,"ResultSetOffset":9000,"TargetCollection":"cases","AndOr":"And","QueryGroups":[{"AndOr":"And","QueryRules":[{"RuleType":0,"Values":["Aviation"],"Columns":["Event.Mode"],"Operator":"contains"},{"RuleType":0,"Values":["1998-01-01","2001-12-31"],"Columns":["Event.EventDate"],"Operator":"is in the range"}]}],"SortColumn":null,"SortDescending":true,"SessionId":241452}

Query text: [
	(Mode) contains (Aviation)
	And
	(EventDate) is in the range (1998-01-01 OR 2001-12-31)
]

