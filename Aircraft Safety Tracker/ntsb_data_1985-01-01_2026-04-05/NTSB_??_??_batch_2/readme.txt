Run time: 05/04/2026 10:17:26

Json query: {"ExportFormat":"data","ResultSetSize":500,"ResultSetOffset":10000,"TargetCollection":"cases","AndOr":"And","QueryGroups":[{"AndOr":"And","QueryRules":[{"RuleType":0,"Values":["Aviation"],"Columns":["Event.Mode"],"Operator":"contains"},{"RuleType":0,"Values":["1990-01-02","1993-12-31"],"Columns":["Event.EventDate"],"Operator":"is in the range"}]}],"SortColumn":null,"SortDescending":true,"SessionId":241452}

Query text: [
	(Mode) contains (Aviation)
	And
	(EventDate) is in the range (1990-01-02 OR 1993-12-31)
]

