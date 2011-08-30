#ifndef _LIST_H_
#define _LIST_H_

#define LIST_NULL UINT32_MAX

struct ListNode {
   uint32_t data;
   ListNode* next;
} ;

//LIST FUNCTIONS

/*
 * create a new list
 */
ListNode*
liNew(uint32_t data);

/*
 * append an existing list node after the given list node
 */
void
liInsertAfter( ListNode *this, ListNode *add) ;

void
liRemoveAfter( ListNode *this ) ;

void
liRemoveRef( ListNode *dummyhead, uint32_t data );

uint32_t
liGetData( ListNode *this );

ListNode*
liGetNext( ListNode *this );

#endif
