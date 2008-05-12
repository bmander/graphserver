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


/*
 * CHANGES:  
 * [2005-07-19] primera version.
 * 
 * TO DO:
 * - Substituir la funcion de ordenacion por una de mas rapida.
 */



#ifndef __LIST_H__
#define __LIST_H__

#ifdef __cplusplus
extern "C" {
#endif

#include <stdio.h>

/**
 * Tipo de representacion de un nodo.
 */
typedef struct list_node_t {

	void *element;
	struct list_node_t *next;
}
list_node_t;

/**
 * Tipo de representacion de una lista.
 */
typedef struct list_t {

	size_t size;
	int (*cmpfunc)(void*, void*);
	list_node_t* head;
	list_node_t* tail;
	list_node_t* iterator;
}
list_t;

/**
 * Crea un tipo lista. 
 *
 * @return list_t*: tipo lista.
 */
void* list_new ();

/**
 * Libera la memoria utilizada por la lista. 
 * Si no se proporciona una funcion para liberar los elementos insertador, 
 * (Pasando NULL como argumento) estos no se liberaran.
 *
 * @param *obj: objeto con el que trabaja.
 * @param freefunc: funcion para liberar la memoria de los elementos.
 */
void list_free (list_t* obj, void (*freefunc)(void*));

/**
 * A~ade un elemento a la lista en la posicion dada.
 *
 * @param *obj: objeto con el que trabaja.
 * @param index: posicion del elemento.
 */
void list_add (list_t* obj, void* element, unsigned int index);

/**
 * A~ade un elemento al principio de la lista.
 *
 * @param *obj: objeto con el que trabaja.
 * @param element: elemento a insertar.
 */
void list_add_first (list_t* obj, void* element);

/**
 * A~ade un elemento al final de la lista.
 *
 * @param *obj: objeto con el que trabaja.
 * @param element: elemento a insertar.
 */
void list_add_last (list_t* obj, void* element);

/**
 * Comprueba si el elemento esta en la lista.
 *
 * @param *obj: objeto con el que trabaja.
 * @param element: elemento buscado.
 * @return int: 1 si contiene el elemente, 0 en caso contrario.
 */
int list_contains (list_t* obj, void *element);

/**
 * Obtiene un elemento de la lista en la posicion dada, NULL si no existe.
 *
 * @param *obj: objeto con el que trabaja.
 * @param index: posicion del elemento.
 * @return void*: apuntador al elemento.
 */
void* list_get (list_t* obj, unsigned int index);

/**
 * Obtiene el primer elemento de la lista, NULL si la lista esta vacia.
 *
 * @param *obj: objeto con el que trabaja.
 * @return void*: apuntador al elemento.
 */
void* list_get_first (list_t* obj);

/**
 * Obtiene el ultimo elemento de la lista, NULL si la lista esta vacia.
 *
 * @param *obj: objeto con el que trabaja.
 * @return void*: apuntador al elemento.
 */
void* list_get_last (list_t* obj);

/**
 * Obtiene el indice de un elemento dado, -1 si no existe.
 *
 * @param *obj: objeto con el que trabaja.
 * @param element: elemento buscado.
 * @return int: indice del elemento o -1 si no lo encuentra.
 */
int list_index_of (list_t* obj, void* element); 

/**
 * Borra de la lista el elemento en la posicion dada, retornando un apuntador
 * al elemento. Si no existe retorna NULL.
 *
 * @param *obj: objeto con el que trabaja.
 * @param index: posicion del elemento.
 * @return void*: apuntador al elemento.
 */
void* list_remove (list_t* obj, unsigned int index);

/**
 * Borra el primer elemento de la lista, retornando un apuntador al mismo. 
 * Si no existe retorna NULL.
 *
 * @param *obj: objeto con el que trabaja.
 * @return void*: apuntador al elemento.
 */
void* list_remove_first (list_t* obj);

/**
 * Borra el ultimo elemento de la lista, retornando un apuntador al mismo. 
 * Si no existe retorna NULL.
 *
 * @param *obj: objeto con el que trabaja.
 * @return void*: apuntador al elemento.
 */
void* list_remove_last (list_t* obj);

/**
 * Reemplaza el elemento en la posicion dada, retornando un apuntador al
 * elemento anterior.
 *
 * @param *obj: objeto con el que trabaja.
 * @param element: elemento nuevo.
 * @param index: posicion del elemento.
 * @return void*: apuntador al elemento.
 */
void* list_set (list_t* obj, void* element, unsigned int index); 

/**
 * Retorna el numero de elementos en la lista.
 *
 * @param *obj: objeto con el que trabaja.
 * @return int: numero de elementos en la lista.
 */
int list_size (list_t* obj);

/**
 * Posiciona un iterador de la lista al principio.
 *
 * @param *obj: objeto con el que trabaja.
 */
void list_begin (list_t* obj);

/**
 * Retorna el elemento al que apunta el iterador y avanza una posicion. 
 *
 * @param *obj: objeto con el que trabaja.
 * @return void*: apuntador al elemento.
 */
void *list_next (list_t* obj);

/**
 * Ordena la lista a partir de una funcion de comparacion personalizada.
 * Es necesario haber establecido con cmpfunc con list_set_cmpfunc().
 * 
 * @param *obj: objeto con el que trabaja.
 * @param desc: 0 para ordenacion normal, 1 para ordenar de forma descenciente.
 */
void list_sort (list_t* obj, int desc);

/**
 * Establece una funcion de comparacion personalizada.
 * 
 * @param *obj: objeto con el que trabaja.
 * @param *cmpfunc(...): funcion de comparacion que retorna 0 si param1=param2,
 *         un entero menor que 1 si param1<param2 y un entero mayor que cero 
 *         si param1>param2.
 */
void list_set_cmpfunc (list_t* obj, int (*cmpfunc)(void*, void*));


#ifdef __cplusplus
}
#endif

#endif







