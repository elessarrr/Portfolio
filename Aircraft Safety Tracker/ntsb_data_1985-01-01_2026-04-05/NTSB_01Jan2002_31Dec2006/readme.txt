Run time: 05/04/2026 10:35:07

Json query: {"ExportFormat":"data","ResultSetSize":500,"ResultSetOffset":10000,"TargetCollection":"cases","AndOr":"And","QueryGroups":[{"AndOr":"And","QueryRules":[{"RuleType":0,"Values":["Aviation"],"Columns":["Event.Mode"],"Operator":"contains"},{"RuleType":0,"Values":["2002-01-01","2006-12-31"],"Columns":["Event.EventDate"],"Operator":"is in the range"}]}],"SortColumn":null,"SortDescending":true,"SessionId":241452}

Query text: [
	(Mode) contains (Aviation)
	And
	(EventDate) is in the range (2002-01-01 OR 2006-12-31)
]

