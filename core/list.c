/*****************************************************************************
 * Copyright (c) 2005  Daniel Lerch Hostalot <http://daniellerch.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a 
 * copy of this software and associated documentation files (the "Software"), 
 * to deal in the Software without restriction, including without limitation 
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, 
 * and/or sell copies of the Software, and to permit persons to whom the 
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in 
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
 * DEALINGS IN THE SOFTWARE.
 ****************************************************************************/

	
#include "list.h"
#include <stdlib.h>


/* ------------------------------------------------------------------------- */
void* list_new ()
{
	list_t* obj;

   obj = malloc(sizeof(list_t));
   if(!obj) {

      perror("list_new()");
      exit(EXIT_FAILURE);
   }

	obj->head = NULL;
	obj->tail = NULL;
	obj->iterator = obj->head;
	obj->size = 0;
	obj->cmpfunc = NULL;

	return obj;
}

/* ------------------------------------------------------------------------- */
void list_free (list_t* obj, void (*freefunc)(void*))
{
	void* elm;

	if (obj->size>0) {

		list_begin(obj);
		while (list_next(obj)) {

			elm = list_remove_first(obj);
			if (freefunc) freefunc(elm);
		}
	}
 
	free(obj);
}

/* ------------------------------------------------------------------------- */
void list_add (list_t* obj, void* element, unsigned int index)
{
	int i;
	list_node_t *node_ptr;
	list_node_t *node_before;
	list_node_t *node_after;
	list_node_t* new_node = malloc(sizeof(list_node_t));

	if(!new_node) {

		perror("list_add()");		
		exit(EXIT_FAILURE);
	}
	
	new_node->element = element;
	new_node->next = NULL;

	if (index > obj->size) {

		fprintf(stderr, "list_add(): ERROR indice fuera de los limites.\n");
		exit(EXIT_FAILURE);
	}

	obj->size++;

	if (!((obj->tail)&&(obj->head))) {

		obj->tail = new_node;
		obj->head = new_node;
		return;
	}

	i=0;
	for (node_ptr=obj->head; node_ptr; node_ptr=node_ptr->next) {
	
		if (i==index) {

			if (i==0) {

				node_after = obj->head;
				obj->head = new_node;
				obj->head->next = node_after;
				break;
			}
			else if (i==obj->size) {

				node_before = node_ptr;
				node_before->next = new_node;
				new_node->next = NULL;
				obj->tail = new_node;
				break;
			}
		}
		else if (i+1==index) {

			node_before = node_ptr;
			node_after = node_ptr->next;
			node_before->next = new_node;
			new_node->next = node_after;
			break;
		}

		i++;
	}
}

/* ------------------------------------------------------------------------- */
void list_add_first (list_t* obj, void* element)
{
	list_add (obj, element, 0);
}

/* ------------------------------------------------------------------------- */
void list_add_last (list_t* obj, void* element)
{
	list_add (obj, element, obj->size);
}

/* ------------------------------------------------------------------------- */
int list_contains (list_t* obj, void *element)
{
	list_node_t* node_ptr;

	for (node_ptr=obj->head; node_ptr; node_ptr=node_ptr->next) {

		if (obj->cmpfunc) {
			if (obj->cmpfunc(element, node_ptr->element)==0) return 1;
		}
		else if (element==node_ptr->element) return 1;
	}

	return 0;
}

/* ------------------------------------------------------------------------- */
void* list_get (list_t* obj, unsigned int index)
{
	int i;
	list_node_t *node_ptr;

	if (index > obj->size) {
		
		fprintf(stderr, "list_get(): ERROR indice fuera de los limites.\n");
		exit(EXIT_FAILURE);
	}

	i=0;
	for (node_ptr=obj->head; node_ptr; node_ptr=node_ptr->next) {

		if (i==index) return node_ptr->element;
		i++;
	}

	/* No deberia llegar aqui */
	return NULL;
}

/* ------------------------------------------------------------------------- */
void* list_get_first (list_t* obj)
{
	return list_get (obj, 0);
}

/* ------------------------------------------------------------------------- */
void* list_get_last (list_t* obj)
{
	if (obj->size>0) return list_get (obj, obj->size-1);
	else return NULL;
}

/* ------------------------------------------------------------------------- */
int list_index_of (list_t* obj, void* element)
{
	int i=0;
	list_node_t* node_ptr;

	for (node_ptr=obj->head; node_ptr; node_ptr=node_ptr->next)
		if (element==node_ptr->element) return i; else i++;

	return -1;
} 

/* ------------------------------------------------------------------------- */
void* list_remove (list_t* obj, unsigned int index)
{
	int i;
	list_node_t *node_ptr;
	list_node_t *node_before;
	void* element_ptr;

	if (index > obj->size) {

		fprintf(stderr, "list_remove(): ERROR indice fuera de los limites.\n");
		exit(EXIT_FAILURE);
	}

	i=0;
	node_before=obj->head;
	for (node_ptr=obj->head; node_ptr; node_ptr=node_ptr->next) {

		if (i==index) {

			if (i==0) obj->head=node_ptr->next;
			if (i==obj->size-1) obj->tail=node_before;
			/* TODO: Revisar este FIX hecho por Mariano */
			node_before->next=node_ptr->next;

			element_ptr = node_ptr->element;
			free(node_ptr);
			obj->size--;
			return element_ptr;
		}
		i++;
		node_before=node_ptr;
	}

	return NULL;
}

/* ------------------------------------------------------------------------- */
void* list_remove_first (list_t* obj)
{
	return list_remove (obj, 0);
}

/* ------------------------------------------------------------------------- */
void* list_remove_last (list_t* obj)
{
	if (obj->size>0) return list_remove (obj, obj->size-1);
	else return NULL;
}

/* ------------------------------------------------------------------------- */
void* list_set (list_t* obj, void* element, unsigned int index)
{
	list_node_t* node_ptr;
	void* old_element;
	int i=0;

	for (node_ptr=obj->head; node_ptr; node_ptr=node_ptr->next) 
		if (i++ == index) break;

	old_element = node_ptr->element;
	node_ptr->element = element;
	
	return old_element;
} 

/* ------------------------------------------------------------------------- */
int list_size (list_t* obj)
{
	return obj->size;
}

/* ------------------------------------------------------------------------- */
void list_begin (list_t* obj)
{
	obj->iterator = obj->head;
}

/* ------------------------------------------------------------------------- */
void *list_next (list_t* obj)
{	
	void *element;

	if (!obj->iterator) return NULL;

	element = obj->iterator->element;
	obj->iterator = obj->iterator->next;

	return element;
}

/* ------------------------------------------------------------------------- */
void list_sort (list_t* obj, int desc)
{
	int i,j, cmp;
	void* tmp;

	if (!obj->cmpfunc) {

		fprintf(stderr, "list_sort(): ERROR no se ha establecido cmpfunc()\n");
		exit(0);
	}

	/* Ordenacion del list poco eficiente: O(n^2)*/
	
	for (i=0;i<obj->size;i++) {
		for (j=0;j<obj->size;j++) {

			cmp = obj->cmpfunc(list_get(obj, i), list_get(obj, j));

			if ((cmp<0)&&(!desc)) cmp=1;	
			else if ((cmp>0)&&(!desc)) cmp=-1;	
				
			if (cmp>0) {
	
				tmp = list_get (obj, i);
				list_set (obj, list_set (obj, tmp, j), i);
			}
		}
	}
}


/* ------------------------------------------------------------------------- */
void list_set_cmpfunc (list_t* obj, int (*cmpfunc)(void*, void*))
{
	obj->cmpfunc=cmpfunc;
}


