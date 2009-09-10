package gtfs;

import gtfs.types.GTFSDate;

import java.lang.reflect.InvocationTargetException;

public class ServiceCalendarDate extends Record{
	
	public String service_id;
	public GTFSDate date;
	public Integer exception_type;

	ServiceCalendarDate(Table table, String[] record) throws SecurityException,
			NoSuchFieldException, IllegalArgumentException,
			IllegalAccessException, InstantiationException,
			InvocationTargetException, NoSuchMethodException {
		super(table, record);
	}
	
	public String toString() {
		return service_id +" "+date+" "+exception_type;
	}

}
