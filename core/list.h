#ifndef LIST_H
#define LIST_H

struct ListNode {
   Edge* data;
   ListNode* next;
} ;

//LIST FUNCTIONS

/*
 * create a new list
 */
ListNode*
liNew(Edge *data);

/*
 * append an existing list node after the given list node
 */
void
liInsertAfter( ListNode *this, ListNode *add) ;

void
liRemoveAfter( ListNode *this ) ;

void
liRemoveRef( ListNode *dummyhead, Edge* data );

Edge*
liGetData( const ListNode *this );

ListNode*
liGetNext( const ListNode *this );

#endif